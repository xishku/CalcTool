#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
徐汇区部门预算PDF爬虫
从 https://www.xuhui.gov.cn/xxgk/portal/article/list?menuType=wgk&code=zxgk_czgk_bmys
爬取所有部门2026年预算PDF，按部门名称分目录存放。

用法:
    python crawl_budget_pdfs.py              # 爬取所有部门2026年预算
    python crawl_budget_pdfs.py --year 2025  # 爬取指定年份
    python crawl_budget_pdfs.py --dry-run    # 仅列出，不下载
"""

import os
import sys
import re
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

import requests

# 修复 Windows 控制台 GBK 编码问题
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ============================================================================
# 配置
# ============================================================================

BASE_URL = "https://www.xuhui.gov.cn"
SPICA = "/xxgk/portal"
PORTAL_URL = f"{BASE_URL}{SPICA}/article/list?menuType=wgk&code=zxgk_czgk_bmys"
DOWNLOAD_API = "https://foa.xh.sh.cn/api/xjh/report/OutExcel"

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "src" / "budget_pdfs_2026"
STATE_FILE = SCRIPT_DIR / "src" / "crawl_state.json"

# 请求控制
REQUEST_DELAY = 0.5   # 请求间隔（秒）
PAGE_TIMEOUT = 30     # 页面请求超时
DOWNLOAD_TIMEOUT = 120  # 下载超时

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
# 第一步：解析主页面，提取所有部门链接
# ============================================================================

def parse_portal_departments(html: str) -> list[dict]:
    """
    从门户页面 HTML 中解析所有部门链接。

    页面结构：
        <div class="title--a"><b>政府部门</b></div>
        <div class="government_sector_part">
            <ul class="list clear">
                <li><a data-code="..." data-remark="...">区教育局</a></li>
                ...
            </ul>
        </div>
        <div class="title--a"><b>街道/镇</b></div>
        <div class="government_sector_part">...</div>

    返回: [{"name": "区教育局", "code": "xhxxgk_jyj_cz_czxx_bmys", "group": "政府部门"}, ...]
    """
    departments = []

    # 页面结构：每组 = <div class="title--a"><b>组名</b></div> + <div class="government_sector_part">...</div>
    # 用组合正则直接匹配 title+sector 成对结构
    group_pattern = (
        r'<div[^>]*class="[^"]*title--a[^"]*"[^>]*>\s*<b[^>]*>(.*?)</b>\s*</div>\s*'
        r'<div[^>]*class="[^"]*government_sector_part[^"]*"[^>]*>(.*?)</div>'
    )
    groups = re.findall(group_pattern, html, re.DOTALL)

    for group_name_raw, sector_html in groups:
        group_name = clean_html_text(group_name_raw)
        if not group_name:
            continue
        extract_sector_links(sector_html, group_name, departments)

    return departments


def clean_html_text(text: str) -> str:
    """清理 HTML 文本：去标签、去多余空白"""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', '', text)
    return text.strip()


def extract_sector_links(sector_html: str, group_name: str, departments: list):
    """
    从 government_sector_part 块的 HTML 中提取所有部门链接。
    每个部门以 <li><a data-code="..." data-remark="...">名称</a></li> 形式存在。
    """
    # HTML 的编码可能导致中文乱码，但 data 属性值始终是 ASCII
    # 部门标签名称从 a 标签文本内容提取（可能是乱码）
    # 备选方案：从 data-remark/code 推断名称

    # 提取所有带 data-code 的 <a> 标签
    links = re.findall(
        r'<a\s+([^>]*?)>(.*?)</a>',
        sector_html, re.DOTALL
    )

    for attrs_str, raw_name in links:
        # 提取 data 属性
        code = re.search(r'data-code="([^"]*)"', attrs_str)
        remark = re.search(r'data-remark="([^"]*)"', attrs_str)
        url_attr = re.search(r'data-url="([^"]*)"', attrs_str)

        if not code and not remark:
            continue

        code_val = (code.group(1) or "").strip() if code else ""
        remark_val = (remark.group(1) or "").strip() if remark else ""
        url_val = (url_attr.group(1) or "").strip() if url_attr else ""

        # 清理名称
        name = clean_html_text(raw_name)
        if not name or len(name) < 2:
            continue

        # 确定最终 URL（优先 remark，其次 code）
        if url_val:
            final_url = url_val if url_val.startswith("http") else BASE_URL + url_val
        elif remark_val:
            final_url = f"{BASE_URL}{SPICA}/article/list?menuType=wgk&code={remark_val}"
        elif code_val:
            final_url = f"{BASE_URL}{SPICA}/article/list?menuType=wgk&code={code_val}"
        else:
            continue

        departments.append({
            "name": name,
            "group": group_name,
            "code": code_val,
            "remark": remark_val,
            "list_url": final_url,
        })


# ============================================================================
# 第二步：从部门列表页提取文章
# ============================================================================

def parse_article_list(html: str, year_filter: str) -> list[dict]:
    """
    从部门列表页 HTML 中提取指定年份的文章。
    返回: [{"id": "xxx", "title": "xxx", "year": "2026"}, ...]
    """
    articles = []
    # 文章链接格式: /xxgk/portal/article/detail?id=HEXID
    matches = re.findall(
        r'<a[^>]*href="/xxgk/portal/article/detail\?id=([a-f0-9]+)"[^>]*>\s*(.*?)\s*</a>',
        html, re.DOTALL
    )
    for aid, title in matches:
        title = re.sub(r'<[^>]+>', '', title).strip()
        title = re.sub(r'\s+', ' ', title)
        if year_filter in title and ("预算" in title or "决算" in title):
            articles.append({"id": aid, "title": title, "year": year_filter})
    return articles


def fetch_article_list(department: dict, year_filter: str) -> list[dict]:
    """获取部门的所有文章列表（处理分页）"""
    all_articles = []
    page = 0
    max_pages = 20  # 安全限制

    while page < max_pages:
        if page == 0:
            url = department["list_url"]
        else:
            url = f"{department['list_url']}&page={page}"

        try:
            r = session.get(url, timeout=PAGE_TIMEOUT)
            if r.status_code != 200:
                break
            articles = parse_article_list(r.text, year_filter)
            if not articles and page > 0:
                break  # 空页面，停止
            all_articles.extend(articles)
            time.sleep(REQUEST_DELAY)
        except Exception as e:
            print(f"  ERROR fetching page {page}: {e}")
            break

        page += 1

    return all_articles


# ============================================================================
# 第三步：从文章详情页提取 PDF 下载链接
# ============================================================================

def extract_pdf_url(article_id: str) -> str | None:
    """
    从文章详情页提取 PDF 下载 URL。
    
    支持两种模式：
    1. imagefileid → OutExcel API（大部分文章用此方式）
    2. 直接的 /xxgk/file/...pdf 链接（部分文章用此方式）
    """
    url = f"{BASE_URL}{SPICA}/article/detail?id={article_id}"
    try:
        r = session.get(url, timeout=PAGE_TIMEOUT)
        if r.status_code != 200:
            return None
            
        # 模式1: imagefileid + OutExcel API
        m = re.search(r'imagefileid=([a-f0-9]+)', r.text)
        if m:
            return f"{DOWNLOAD_API}?imagefileid={m.group(1)}"
        
        # 模式2: 直接 PDF 文件链接
        m2 = re.search(r'href="(/xxgk/file/[^"]+\.pdf)"', r.text)
        if m2:
            pdf_path = m2.group(1)
            return BASE_URL + pdf_path
            
    except Exception as e:
        print(f"    ERROR extracting pdf url: {e}")
    return None


# ============================================================================
# 第四步：下载 PDF
# ============================================================================

def download_pdf(pdf_url: str, save_path: Path) -> bool:
    """下载 PDF 并保存到指定路径"""
    try:
        r = session.get(pdf_url, timeout=DOWNLOAD_TIMEOUT)
        if r.status_code != 200:
            print(f"    HTTP {r.status_code}")
            return False
        if not r.content or len(r.content) < 100:
            print(f"    Content too small: {len(r.content)} bytes")
            return False
        # 验证 PDF 头
        if r.content[:5] != b'%PDF-':
            print(f"    Not a valid PDF (first bytes: {r.content[:20]})")
            return False
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(r.content)
        return True
    except Exception as e:
        print(f"    ERROR downloading: {e}")
        return False


def sanitize_filename(name: str) -> str:
    """清理文件名中的非法字符"""
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', '', name)
    return name[:200]


# ============================================================================
# 状态管理（支持断点续传）
# ============================================================================

def load_state() -> dict:
    """加载爬取状态"""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"completed": {}, "failed": {}}


def save_state(state: dict):
    """保存爬取状态"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ============================================================================
# 主流程
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="爬取徐汇区部门预算PDF")
    parser.add_argument("--year", default="2026", help="目标年份（默认2026）")
    parser.add_argument("--dry-run", action="store_true", help="仅列出，不下载")
    parser.add_argument("--output", default=None, help="输出目录")
    parser.add_argument("--resume", action="store_true", help="断点续传")
    parser.add_argument("--departments", default=None, help="仅处理指定部门（逗号分隔的名称关键词）")
    args = parser.parse_args()

    output_dir = Path(args.output) if args.output else OUTPUT_DIR
    year_filter = args.year

    print("=" * 60)
    print(f"徐汇区部门预算PDF爬虫")
    print(f"目标年份: {year_filter}")
    print(f"输出目录: {output_dir}")
    print(f"模式: {'预览模式 (不下载)' if args.dry_run else '下载模式'}")
    print("=" * 60)
    print()

    # 加载状态
    state = load_state() if args.resume else {"completed": {}, "failed": {}}

    # 第一步：获取部门列表
    print("[1/4] 获取部门列表...")
    r = session.get(PORTAL_URL, timeout=PAGE_TIMEOUT)
    if r.status_code != 200:
        print(f"ERROR: 无法访问门户页面 (HTTP {r.status_code})")
        return
    departments = parse_portal_departments(r.text)
    print(f"  找到 {len(departments)} 个部门\n")

    # 过滤部门
    if args.departments:
        keywords = [k.strip() for k in args.departments.split(",")]
        departments = [d for d in departments if any(k in d["name"] for k in keywords)]
        print(f"  过滤后剩余 {len(departments)} 个部门\n")

    # 按组显示
    current_group = None
    for d in departments:
        if d["group"] != current_group:
            current_group = d["group"]
            print(f"\n  --- {current_group} ---")
        print(f"    {d['name']}")

    print(f"\n[2/4] 扫描各部门文章列表...\n")

    # 汇总
    total_articles = 0
    total_downloaded = 0
    total_skipped = 0
    total_failed = 0

    for i, dept in enumerate(departments):
        dept_name = dept["name"]
        dept_key = dept_name

        # 跳过已完成的
        if dept_key in state["completed"] and args.resume:
            print(f"  [{i+1}/{len(departments)}] {dept_name} [已处理，跳过]")
            continue

        print(f"  [{i+1}/{len(departments)}] {dept_name} ...", end=" ", flush=True)
        articles = fetch_article_list(dept, year_filter)

        if not articles:
            print(f"无{year_filter}年预算数据")
            state["completed"][dept_key] = {"articles": 0, "downloaded": 0}
            total_skipped += 1
            continue

        print(f"找到 {len(articles)} 篇{year_filter}年文章")
        total_articles += len(articles)

        if args.dry_run:
            for art in articles[:5]:
                print(f"      {art['title']}")
            if len(articles) > 5:
                print(f"      ... 还有 {len(articles)-5} 篇")
            continue

        # 第三步 & 第四步：下载
        dept_downloaded = 0
        dept_failed = 0
        dept_no_attachment = 0
        for art in articles:
            # 获取 PDF 下载链接
            pdf_url = extract_pdf_url(art["id"])
            if not pdf_url:
                print(f"    [SKIP] {art['title']}: 无附件（PDF未上传或已撤回）")
                dept_no_attachment += 1
                continue

            # 构建文件名和路径
            safe_name = sanitize_filename(art["title"])
            save_path = output_dir / dept_name / f"{safe_name}.pdf"

            # 跳过已存在
            if save_path.exists():
                dept_downloaded += 1
                continue

            # 下载
            time.sleep(REQUEST_DELAY)
            if download_pdf(pdf_url, save_path):
                dept_downloaded += 1
            else:
                dept_failed += 1
                print(f"    ✗ {art['title']}: 下载失败")

        total_downloaded += dept_downloaded
        total_failed += dept_failed
        state["completed"][dept_key] = {
            "articles": len(articles),
            "downloaded": dept_downloaded,
            "failed": dept_failed,
            "no_attachment": dept_no_attachment,
        }
        save_state(state)

    # 汇总报告
    print(f"\n{'=' * 60}")
    print(f"完成！")
    print(f"  部门总数:    {len(departments)}")
    print(f"  含{year_filter}年数据: {total_skipped + total_articles}")
    print(f"  文章总数:    {total_articles}")
    if not args.dry_run:
        print(f"  下载成功:    {total_downloaded}")
        print(f"  下载失败:    {total_failed}")
    print(f"  输出目录:    {output_dir}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
