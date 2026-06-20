#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上海市人民政府 2026年部门预算 PDF 爬虫
来源: https://www.shanghai.gov.cn/bmys-26/index.html

结构:
  首页 → 7个分类页（党委部门/政府部门/人大政协/民主党派/司法机关/人民团体/其他）
  分类页 → 各部门页
  部门页 → PDF 直接下载链接

输出目录结构:
  output/{分类名}/{部门名}/{PDF文件名}.pdf
"""

import os
import re
import json
import time
import sys
from pathlib import Path
from datetime import datetime

import requests

# 修复 Windows 控制台编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ============================================================================
# 配置
# ============================================================================

BASE_URL = "https://www.shanghai.gov.cn"
INDEX_URL = f"{BASE_URL}/bmys-26/index.html"

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "src" / "shanghai_budget_2026"
STATE_FILE = OUTPUT_DIR / "crawl_state.json"

REQUEST_DELAY = 0.5
PAGE_TIMEOUT = 30
DOWNLOAD_TIMEOUT = 120
MAX_RETRIES = 3

session = requests.Session()
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
    """GET 请求（带重试）"""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(url, timeout=timeout)
            r.encoding = 'utf-8'
            return r
        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
            else:
                raise
    return None


def sanitize(name):
    """清理目录/文件名中的非法字符"""
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', '', name)
    return name[:200]


def extract_links(html, base=BASE_URL):
    """
    从 HTML 中提取链接文本和URL。
    适配上海市预算站点的列表格式：
    <li><i class="..."></i><a href="/bmys-26-xxx/index.html" target="_blank">名称</a><span>(N)</span></li>
    """
    results = []
    # 匹配 <a> 标签中的 href 和文本，忽略图标、span 等
    pattern = r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>'
    for match in re.finditer(pattern, html, re.DOTALL):
        href = match.group(1)
        text = re.sub(r'<[^>]+>', '', match.group(2)).strip()
        text = re.sub(r'\s+', '', text)
        if not text or len(text) < 2:
            continue
        # 拼接完整 URL
        if href.startswith('http'):
            full_url = href
        elif href.startswith('/'):
            full_url = base + href
        else:
            full_url = base + '/' + href
        results.append((text, full_url))
    return results


# ============================================================================
# 状态管理
# ============================================================================

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"downloaded": {}, "failed": {}, "categories": {}}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ============================================================================
# 爬虫核心
# ============================================================================

class ShanghaiBudgetCrawler:
    def __init__(self):
        self.state = load_state()
        self.total_pdfs = 0
        self.downloaded = 0
        self.failed = 0
        self.skipped = 0
        self._dry_run = False
        self._test_limit = 0

    def parse_categories(self, html):
        """
        从首页解析 7 个分类链接。
        首页格式：<li><a href="/bmys-26-001/index.html">党委部门</a><span>(17)</span></li>
        """
        categories = []
        pattern = r'<a[^>]*href="(/bmys-26-0\d+/index\.html)"[^>]*>([^<]+)</a>'
        for m in re.finditer(pattern, html):
            href = m.group(1)
            name = m.group(2).strip()
            # 排除年份链接（/bmys-26/index.html 匹配不上因为需要 3 位数字后缀）
            if name and len(name) >= 2:
                categories.append((name, BASE_URL + href))
        
        # 去重（保留顺序）
        seen = set()
        unique = []
        for name, url in categories:
            if url not in seen:
                seen.add(url)
                unique.append((name, url))
        return unique

    def parse_category_page(self, html):
        """
        从分类页解析各部门链接。
        格式：<a href="/bmys-26-dw001/index.html">中共上海市委办公厅</a>
        """
        # 7 个分类页的 URL 模式，需要排除（它们会出现在每个分类页的导航中）
        CATEGORY_PATTERNS = tuple(
            f'/bmys-26-{i:03d}/index.html' for i in range(1, 8)
        )

        departments = []
        pattern = r'<a[^>]*href="(/bmys-26-[a-z0-9]+/index\.html)"[^>]*>([^<]+)</a>'
        for m in re.finditer(pattern, html):
            href = m.group(1)
            name = m.group(2).strip()
            name = re.sub(r'\s+', '', name)
            if not name or len(name) < 3:
                continue
            # 过滤掉分类导航链接（如 /bmys-26-001/index.html）
            if href.startswith(CATEGORY_PATTERNS):
                continue
            departments.append((name, BASE_URL + href))

        # 去重
        seen = set()
        unique = []
        for name, url in departments:
            if url not in seen:
                seen.add(url)
                unique.append((name, url))
        return unique

    def parse_department_page(self, html):
        """
        从部门页解析 PDF 下载链接。
        格式：<a href="/cmsres/xx/xxxx.pdf">单位名称2026年度预算</a>
        只下载 2026 年的（链接文本中包含 2026）
        """
        pdfs = []
        pattern = r'<a[^>]*href="(/cmsres/[^"]+\.pdf)"[^>]*>([^<]+)</a>'
        for m in re.finditer(pattern, html):
            href = m.group(1)
            label = m.group(2).strip()
            label = re.sub(r'\s+', '', label)
            # 只取 2026 年的
            if '2026' not in label:
                continue
            pdfs.append((label, BASE_URL + href))
        return pdfs

    def download_pdf(self, url, save_path):
        """下载并验证 PDF"""
        try:
            r = session.get(url, timeout=DOWNLOAD_TIMEOUT)
            if r.status_code != 200:
                print(f"      HTTP {r.status_code}")
                return False
            # 验证 PDF 头
            if r.content[:5] != b'%PDF-':
                print(f"      非有效PDF (前20字节: {r.content[:20]})")
                return False
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_bytes(r.content)
            return True
        except Exception as e:
            print(f"      ERROR: {e}")
            return False

    def run(self):
        print("=" * 60)
        print("上海市2026年部门预算 PDF 爬虫")
        print(f"入口: {INDEX_URL}")
        print(f"输出: {OUTPUT_DIR}")
        print("=" * 60)

        # Step 1: 获取首页，解析分类
        print("\n[1/3] 获取分类列表...")
        r = fetch(INDEX_URL)
        if not r or r.status_code != 200:
            print("ERROR: 无法访问首页")
            return
        categories = self.parse_categories(r.text)
        print(f"  找到 {len(categories)} 个分类:")
        for name, url in categories:
            print(f"    - {name}: {url}")

        # Step 2: 遍历每个分类 → 部门
        print("\n[2/3] 扫描各部门...")
        all_depts = []  # [(category_name, dept_name, dept_url)]

        for cat_name, cat_url in categories:
            print(f"\n  [{cat_name}]")
            time.sleep(REQUEST_DELAY)
            r = fetch(cat_url)
            if not r or r.status_code != 200:
                print(f"    ERROR: 无法访问")
                continue
            departments = self.parse_category_page(r.text)
            print(f"    找到 {len(departments)} 个部门")
            for dept_name, dept_url in departments[:3]:
                print(f"      {dept_name}")
            if len(departments) > 3:
                print(f"      ... 还有 {len(departments)-3} 个")
            for dept_name, dept_url in departments:
                all_depts.append((cat_name, dept_name, dept_url))

        print(f"\n  总计: {len(all_depts)} 个部门")

        # 测试模式：限制部门数
        if self._test_limit > 0:
            all_depts = all_depts[:self._test_limit]
            print(f"  (测试模式，仅处理 {len(all_depts)} 个部门)")

        # Step 3: 遍历每个部门，下载 PDF
        print("\n[3/3] 下载 PDF...")
        for i, (cat_name, dept_name, dept_url) in enumerate(all_depts):
            state_key = f"{sanitize(cat_name)}/{sanitize(dept_name)}"

            # 跳过已完成的部门
            if state_key in self.state["downloaded"]:
                self.skipped += 1
                continue

            print(f"\n  [{i+1}/{len(all_depts)}] {cat_name} > {dept_name}")
            time.sleep(REQUEST_DELAY)

            r = fetch(dept_url)
            if not r or r.status_code != 200:
                print(f"    ERROR: 无法访问部门页")
                self.state["failed"][state_key] = "页面访问失败"
                continue

            pdfs = self.parse_department_page(r.text)
            if not pdfs:
                print(f"    无2026年PDF")
                self.state["downloaded"][state_key] = []
                self.skipped += 1
                continue

            print(f"    找到 {len(pdfs)} 个PDF")
            downloaded_list = []
            for pdf_label, pdf_url in pdfs:
                self.total_pdfs += 1
                pdf_filename = sanitize(pdf_label) + ".pdf"
                save_path = OUTPUT_DIR / sanitize(cat_name) / sanitize(dept_name) / pdf_filename

                if self._dry_run:
                    print(f"      [PDF] {pdf_label} -> {save_path}")
                    downloaded_list.append(pdf_label)
                    continue

                if save_path.exists() and save_path.stat().st_size > 0:
                    print(f"      [SKIP] {pdf_label}")
                    downloaded_list.append(pdf_label)
                    continue

                print(f"      下载: {pdf_label}")
                time.sleep(REQUEST_DELAY / 2)

                if self.download_pdf(pdf_url, save_path):
                    size_kb = save_path.stat().st_size / 1024
                    print(f"        OK ({size_kb:.1f} KB)")
                    self.downloaded += 1
                    downloaded_list.append(pdf_label)
                else:
                    print(f"        FAIL")
                    self.failed += 1

            if downloaded_list:
                self.state["downloaded"][state_key] = downloaded_list
            if not self._dry_run:
                save_state(self.state)

        # 汇总
        print("\n" + "=" * 60)
        print("完成！")
        print(f"  部门总数:      {len(all_depts)}")
        print(f"  PDF总数:       {self.total_pdfs}")
        print(f"  下载成功:      {self.downloaded}")
        print(f"  下载失败:      {self.failed}")
        print(f"  跳过:          {self.skipped}")
        print(f"  输出目录:      {OUTPUT_DIR}")
        print("=" * 60)

        save_state(self.state)


# ============================================================================
# 入口
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="上海市2026年部门预算PDF爬虫")
    parser.add_argument("--dry-run", action="store_true", help="仅列出，不下载")
    parser.add_argument("--test", type=int, default=0, help="仅测试前N个部门")
    args = parser.parse_args()

    crawler = ShanghaiBudgetCrawler()

    if args.dry_run:
        print("*** 预览模式（不下载）***\n")
        crawler._dry_run = True
    elif args.test > 0:
        print(f"*** 测试模式（仅前{args.test}个部门）***\n")
        crawler._test_limit = args.test

    crawler.run()


if __name__ == "__main__":
    main()
