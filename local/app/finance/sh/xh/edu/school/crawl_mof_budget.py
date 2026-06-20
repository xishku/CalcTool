#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财政部中央部门预算 2026年 PDF 爬虫
来源: https://www.mof.gov.cn/zyyjsgkpt/zybmyjs/bmys/

结构:
  列表页（35页，2026年仅在第1页）→ 条目链接
  条目链接有3种:
    1. 直接 PDF → 直接下载
    2. mof.gov.cn 详情页 → 找外部URL或PDF链接
    3. 外部网站 HTML → 解析页面找PDF

输出目录结构:
  output/{部门名称}/{PDF文件名}.pdf
"""

import os
import re
import json
import time
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
import urllib3
urllib3.disable_warnings()

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ============================================================================
# 配置
# ============================================================================

BASE_URL = "https://www.mof.gov.cn"
LIST_URL = f"{BASE_URL}/zyyjsgkpt/zybmyjs/bmys/"
INDEX_URL = f"{LIST_URL}index.html"

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "src" / "mof_budget_2026"
STATE_FILE = OUTPUT_DIR / "crawl_state.json"

REQUEST_DELAY = 0.5
PAGE_TIMEOUT = 30
DOWNLOAD_TIMEOUT = 120
MAX_RETRIES = 3
MAX_PAGES = 5  # 2026年预算基本都在第1页

session = requests.Session()
session.verify = False
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
})


# ============================================================================
# 工具函数
# ============================================================================

def fetch(url, timeout=PAGE_TIMEOUT):
    """GET 请求（带重试，忽略SSL）"""
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(url, timeout=timeout, verify=False)
            r.encoding = r.apparent_encoding or 'utf-8'
            return r
        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
    print(f"      [ERROR] {last_err}")
    return None


def sanitize(name):
    """清理目录/文件名"""
    name = re.sub(r'[<>:"/\\|?*\r\n\t]+', '_', name)
    name = re.sub(r'\s+', '', name)
    name = re.sub(r'^(中华人民共和国|中国)', '', name)
    return name[:200]


def make_absolute(href, base_url):
    """将相对URL转为绝对URL"""
    if href.startswith('http://') or href.startswith('https://'):
        return href
    if href.startswith('//'):
        return 'https:' + href
    if href.startswith('./'):
        href = href[2:]  # 去掉 ./
    if href.startswith('/'):
        # 使用 base_url 的域名部分
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{href}"
    return urljoin(base_url, href)


# ============================================================================
# 状态管理
# ============================================================================

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"downloaded": {}, "failed": {}, "no_pdf": {}}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ============================================================================
# 爬虫核心
# ============================================================================

class MofBudgetCrawler:
    def __init__(self):
        self.state = load_state()
        self.total_pdfs = 0
        self.downloaded = 0
        self.failed = 0
        self.skipped = 0
        self.no_pdf = 0
        self._dry_run = False
        self._test_limit = 0

    # ------------------------------------------------------------------
    # Step 1: 解析列表页，提取2026年条目
    # ------------------------------------------------------------------

    def parse_list_page(self, html):
        """从列表页HTML中提取2026年预算条目"""
        entries = []
        
        # 方法1：提取所有title属性包含"2026"的链接
        a_pattern = r'<a[^>]*href="([^"]*)"[^>]*title="([^"]*)"[^>]*>(.*?)</a>'
        for m in re.finditer(a_pattern, html, re.DOTALL):
            href = m.group(1)
            title = m.group(2).strip()
            text = re.sub(r'<[^>]+>', '', m.group(3)).strip()
            label = title or text or ''
            label = re.sub(r'\s+', '', label)
            if not label or len(label) < 3:
                continue
            # 检查上下文是否包含2026，且标题不含2025
            start = max(0, m.start() - 300)
            context = html[start:m.end() + 100]
            if '2026' not in context:
                continue
            # 如果标题明确是2025年，跳过
            if '2025' in label and '2026' not in label:
                continue
            # 过滤导航
            if href in ('javascript:;', '#'):
                continue
            if re.match(r'^index[_\d]*\.html$', href):
                continue
            entries.append((label, href))

        # 方法2：更宽泛地找所有链接中上下文有2026的
        if len(entries) < 3:
            simple = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', html, re.DOTALL)
            for href, raw_text in simple:
                if href in ('javascript:;', '#'):
                    continue
                text = re.sub(r'<[^>]+>', '', raw_text).strip()
                text = re.sub(r'\s+', '', text)
                if not text or len(text) < 3:
                    continue
                # 跳过标题明确是2025年的
                if '2025' in text and '2026' not in text:
                    continue
                # 在整页中查找此链接附近的上下文
                pos = html.find(href)
                if pos > 0:
                    ctx = html[max(0,pos-300):pos+300]
                    if '2026' in ctx and ('2026-03' in ctx or '2026年' in ctx or '2026年度' in ctx):
                        entries.append((text, href))

        # 去重
        seen = set()
        unique = []
        for name, href in entries:
            url = make_absolute(href, LIST_URL)
            key = url
            if key not in seen:
                seen.add(key)
                unique.append((name, url))
        return unique

    # ------------------------------------------------------------------
    # Step 2: 从页面提取PDF链接
    # ------------------------------------------------------------------

    def find_pdfs_in_page(self, html, base_url):
        """从HTML页面中找所有PDF链接"""
        pdf_urls = set()
        
        # 找 <a> 标签中的 .pdf 链接
        a_links = re.findall(r'<a[^>]*href=["\']([^"\']*\.pdf)["\']', html, re.IGNORECASE)
        for href in a_links:
            full = make_absolute(href, base_url)
            pdf_urls.add(full)
        
        # 找其他属性中的 .pdf 引用 (src, data-src 等)
        other = re.findall(r'''["']([^"'\s]*\.pdf)["']''', html, re.IGNORECASE)
        for href in other:
            full = make_absolute(href, base_url)
            pdf_urls.add(full)
        
        return list(pdf_urls)

    def find_external_urls(self, html):
        """从HTML中提取所有外部URL（非mof.gov.cn）"""
        urls = set()
        # 找所有绝对URL
        found = re.findall(r'(https?://[^\s"\'<>#]+)', html)
        for u in found:
            u = u.rstrip('.,;:')
            parsed = urlparse(u)
            if 'mof.gov.cn' not in parsed.netloc and parsed.netloc:
                urls.add(u)
        return list(urls)

    # ------------------------------------------------------------------
    # Step 3: 处理外部链接
    # ------------------------------------------------------------------

    def process_external_page(self, url):
        """访问外部页面，提取所有2026年预算相关PDF链接"""
        r = fetch(url)
        if not r or r.status_code != 200:
            return []
        
        html = r.text
        pdfs = self.find_pdfs_in_page(html, url)
        
        # 过滤：只保留可能与预算相关的PDF
        budget_pdfs = []
        for pdf_url in pdfs:
            fn = Path(urlparse(pdf_url).path).name.lower()
            # 跳过明显不是预算的（如css、icon、banner等）
            if any(kw in fn for kw in ['icon', 'logo', 'banner', 'css', 'js', 'bootstrap', 'jquery', 'style']):
                continue
            budget_pdfs.append(pdf_url)
        
        return budget_pdfs

    # ------------------------------------------------------------------
    # 主流程：处理一个条目
    # ------------------------------------------------------------------

    def _do_download(self, pdf_url, dept_name, save_path):
        """下载单个PDF并返回是否成功"""
        if self._dry_run:
            print(f"      -> {save_path}")
            return True
        
        if save_path.exists() and save_path.stat().st_size > 0:
            print(f"      [SKIP] 已存在")
            return True
        
        print(f"      下载: {save_path.name}")
        time.sleep(REQUEST_DELAY / 2)
        
        try:
            r = session.get(pdf_url, timeout=DOWNLOAD_TIMEOUT, allow_redirects=True, verify=False)
            if r.status_code != 200:
                print(f"        HTTP {r.status_code}")
                return False
            if r.content[:5] != b'%PDF-':
                print(f"        非有效PDF (前10字节: {r.content[:10]})")
                return False
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_bytes(r.content)
            size_kb = save_path.stat().st_size / 1024
            print(f"        OK ({size_kb:.1f} KB)")
            return True
        except Exception as e:
            print(f"        ERROR: {e}")
            return False

    def process_entry(self, dept_name, dept_url):
        """处理单个2026年预算条目"""
        state_key = sanitize(dept_name)
        
        if state_key in self.state["downloaded"]:
            self.skipped += 1
            return
        
        # 收集所有候选PDF
        all_pdfs = []
        
        # === 情况1：直接PDF ===
        if dept_url.lower().endswith('.pdf'):
            print(f"    [直接PDF]")
            all_pdfs = [dept_url]
        
        # === 情况2：mof.gov.cn 详情页 ===
        elif 'mof.gov.cn' in dept_url:
            print(f"    [mof详情页]")
            r = fetch(dept_url)
            if not r or r.status_code != 200:
                print(f"      FAIL: 页面不可访问")
                self.failed += 1
                self.state["failed"][state_key] = dept_url
                return
            
            html = r.text
            
            # 先找页面中的直接PDF链接
            pdfs = self.find_pdfs_in_page(html, dept_url)
            
            # 也在所有URL中找PDF（有时PDF以纯文本URL出现）
            if not pdfs:
                ext_urls = self.find_external_urls(html)
                pdf_urls = [u for u in ext_urls if u.lower().endswith('.pdf')]
                if pdf_urls:
                    print(f"      文本中找到 {len(pdf_urls)} 个PDF URL")
                    all_pdfs = pdf_urls
                else:
                    # 过滤相关外部链接
                    relevant_ext = [u for u in ext_urls if 
                        any(d in u for d in ['gov.cn', '/art/', '/content/', 'bmyjs', '预算'])
                        and not any(skip in u for skip in ['beian', 'miit', 'w3.org', 'conac'])]
                    
                    if relevant_ext:
                        print(f"      尝试 {len(relevant_ext)} 个外部链接...")
                        for ext_url in relevant_ext[:3]:
                            if ext_url.lower().endswith('.pdf'):
                                continue  # 已处理
                            time.sleep(REQUEST_DELAY)
                            ext_pdfs = self.process_external_page(ext_url)
                            if ext_pdfs:
                                all_pdfs = ext_pdfs
                                break
                    
                    if not all_pdfs:
                        print(f"      无PDF附件")
                        self.no_pdf += 1
                        self.state["no_pdf"][state_key] = dept_url
                        return
            else:
                print(f"      页面内找到 {len(pdfs)} 个PDF")
                all_pdfs = pdfs
        
        # === 情况3：外部HTML页面 ===
        else:
            print(f"    [外部链接]")
            all_pdfs = self.process_external_page(dept_url)
            
            if not all_pdfs:
                print(f"      无PDF（SSL错误或页面无附件）")
                self.no_pdf += 1
                self.state["no_pdf"][state_key] = dept_url
                return
        
        # === 下载所有找到的PDF ===
        if not all_pdfs:
            print(f"      未找到PDF")
            self.no_pdf += 1
            self.state["no_pdf"][state_key] = dept_url
            return
        
        print(f"      共找到 {len(all_pdfs)} 个PDF")
        downloaded_list = []
        
        for i, pdf_url in enumerate(all_pdfs):
            self.total_pdfs += 1
            if i == 0 and len(all_pdfs) == 1:
                filename = sanitize(dept_name) + ".pdf"
            else:
                # 从URL提取文件名
                fn = Path(urlparse(pdf_url).path).stem
                if fn and len(fn) > 3:
                    filename = sanitize(f"{dept_name}_{fn}") + ".pdf"
                else:
                    filename = sanitize(f"{dept_name}_{i+1}") + ".pdf"
            
            save_path = OUTPUT_DIR / state_key / filename
            
            if self._do_download(pdf_url, dept_name, save_path):
                self.downloaded += 1
                downloaded_list.append(pdf_url)
            else:
                self.failed += 1
        
        if downloaded_list:
            self.state["downloaded"][state_key] = downloaded_list

    # ------------------------------------------------------------------
    # 主运行
    # ------------------------------------------------------------------

    def run(self):
        print("=" * 60)
        print("财政部中央部门2026年预算 PDF 爬虫")
        print(f"入口: {INDEX_URL}")
        print(f"输出: {OUTPUT_DIR}")
        print("=" * 60)

        # Step 1: 爬取列表页
        print("\n[1/3] 爬取列表页...")
        all_entries = []
        
        for page_idx in range(MAX_PAGES):
            if page_idx == 0:
                url = INDEX_URL
                label = "第1页"
            elif page_idx == 1:
                url = f"{LIST_URL}index_1.html"
                label = "第1页(alt)"
            else:
                url = f"{LIST_URL}index_{page_idx}.html"
                label = f"第{page_idx+1}页"
            
            time.sleep(REQUEST_DELAY)
            r = fetch(url)
            if not r or r.status_code != 200:
                if page_idx > 1:
                    break
                continue
            
            entries = self.parse_list_page(r.text)
            print(f"  {label}: {len(entries)} 个2026年条目")
            all_entries.extend(entries)
        
        # 去重
        seen_url = set()
        unique = []
        for name, url in all_entries:
            if url not in seen_url:
                seen_url.add(url)
                unique.append((name, url))
        all_entries = unique
        
        print(f"\n  去重后: {len(all_entries)} 个2026年条目")
        
        if self._test_limit > 0:
            all_entries = all_entries[:self._test_limit]
            print(f"  (测试模式，仅处理前 {self._test_limit} 个)")

        # Step 2: 显示并处理
        print(f"\n[2/3] 条目列表:")
        for i, (name, url) in enumerate(all_entries):
            url_type = "PDF" if url.lower().endswith('.pdf') else \
                       "mof详情" if 'mof.gov.cn' in url else "外部链接"
            print(f"  [{i+1}] {name} [{url_type}]")

        if self._dry_run:
            print(f"\n  *** 预览模式结束 ***")
            return

        print(f"\n[3/3] 下载PDF...")
        for i, (dept_name, dept_url) in enumerate(all_entries):
            print(f"\n  [{i+1}/{len(all_entries)}] {dept_name}")
            time.sleep(REQUEST_DELAY)
            self.process_entry(dept_name, dept_url)
            save_state(self.state)

        # 汇总
        print("\n" + "=" * 60)
        print("完成！")
        print(f"  条目总数:      {len(all_entries)}")
        print(f"  下载成功:      {self.downloaded}")
        print(f"  下载失败:      {self.failed}")
        print(f"  跳过:          {self.skipped}")
        print(f"  无PDF:         {self.no_pdf}")
        print(f"  输出目录:      {OUTPUT_DIR}")
        print("=" * 60)
        save_state(self.state)


# ============================================================================
# 入口
# ============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="财政部2026年部门预算PDF爬虫")
    parser.add_argument("--dry-run", action="store_true", help="仅列出，不下载")
    parser.add_argument("--test", type=int, default=0, help="仅测试前N个条目")
    args = parser.parse_args()

    crawler = MofBudgetCrawler()
    if args.dry_run:
        print("*** 预览模式（不下载）***\n")
        crawler._dry_run = True
    elif args.test > 0:
        print(f"*** 测试模式（仅前{args.test}个条目）***\n")
        crawler._test_limit = args.test
    crawler.run()


if __name__ == "__main__":
    main()
