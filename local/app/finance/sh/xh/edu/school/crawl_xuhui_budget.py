#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
徐汇区各部门2026年预算 PDF 爬虫

目标页面: https://www.xuhui.gov.cn/xxgk/portal/article/list?menuType=wgk&code=zxgk_czgk_bmys
结构: 导航页 -> 各部门列表页 -> 详情页 -> PDF附件

输出: src/xuhui_budget_2026/{部门名称}/{文章标题}.pdf
"""

import os, re, sys, json, time, random, requests
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except: pass

# ========== 配置 ==========
BASE_URL = "https://www.xuhui.gov.cn"
LIST_TEMPLATE = "https://www.xuhui.gov.cn/xxgk/portal/article/list?menuType=wgk&code={code}&page={page}"
OUTPUT_ROOT = Path(__file__).parent / "src" / "xuhui_budget_2026"
STATE_FILE = OUTPUT_ROOT / "crawl_state.json"

REQUEST_DELAY = (0.8, 2.0)
MAX_RETRIES = 3
PAGE_TIMEOUT = 30
DOWNLOAD_TIMEOUT = 120

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

session = requests.Session()
session.headers.update(HEADERS)
session.verify = False
requests.packages.urllib3.disable_warnings()


def fetch(url, timeout=PAGE_TIMEOUT):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(url, timeout=timeout)
            r.encoding = r.apparent_encoding or 'utf-8'
            return r
        except Exception as e:
            if attempt >= MAX_RETRIES:
                return None
            time.sleep(2 ** attempt)
    return None


def sanitize(name):
    """清理目录/文件名中的非法字符"""
    for ch in '<>:"/\\|?*':
        name = name.replace(ch, '_')
    name = re.sub(r'\s+', '', name)
    if len(name) > 80:
        name = name[:80]
    return name


def load_departments():
    """从 _departments.json 加载部门列表"""
    dept_file = Path(__file__).parent / "_departments.json"
    with open(dept_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    depts = []
    seen_names = set()
    for d in data:
        if not d.get('remark'):
            continue
        name = sanitize(d['name'])
        if name in seen_names:
            continue
        seen_names.add(name)
        depts.append({
            'name': name,
            'code': d['remark'],
            'list_url': d['list_url'] if d.get('url') else None,
        })
    return depts


def load_state():
    """加载断点续传状态"""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'completed': [], 'failed': {}, 'stats': {'total_pdfs': 0, 'total_size': 0}}


def save_state(state):
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def parse_list_page(code, page_no):
    """解析部门列表页，返回文章列表"""
    url = LIST_TEMPLATE.format(code=code, page=page_no)
    r = fetch(url)
    if not r or r.status_code != 200:
        return []

    html = r.text

    # 获取总页数
    total_match = re.search(r'共(\d+)页', html)
    total_pages = int(total_match.group(1)) if total_match else 0

    # 解析表格中的文章链接
    articles = []
    # 方法1: 找 a.li_title 或类似表格中的链接
    table_rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
    for row in table_rows:
        links = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', row, re.DOTALL)
        title_link = None
        date_text = ""
        for href, text in links:
            text = re.sub(r'<[^>]+>', '', text).strip()
            if 'id=' in href and len(text) > 2:
                title_link = (href, text)
            elif re.match(r'\d{4}-\d{2}-\d{2}', text):
                date_text = text

        if title_link:
            href, title = title_link
            article_id = href.split('id=')[-1] if 'id=' in href else None
            article_url = BASE_URL + href if href.startswith('/') else href
            articles.append({
                'id': article_id,
                'title': re.sub(r'\s+', '', title),
                'date': date_text,
                'url': article_url,
            })

    return articles, total_pages


def parse_detail_page(article_url):
    """解析详情页，提取PDF附件链接"""
    r = fetch(article_url)
    if not r or r.status_code != 200:
        return []

    html = r.text
    pdfs = []

    # 方法1: attachment_part 中的链接
    attach_match = re.search(r'<div[^>]*class="attachment_part"[^>]*>(.*?)</div>', html, re.DOTALL)
    if attach_match:
        attach_html = attach_match.group(1)
        links = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', attach_html, re.DOTALL)
        for href, raw_text in links:
            text = re.sub(r'<[^>]+>', '', raw_text).strip()
            if 'imagefileid=' in href or href.lower().endswith('.pdf'):
                filename = text if ('.' in text) else f"{text}.pdf"
                pdfs.append({'url': href, 'filename': filename})

    # 方法2: 页面中所有带 imagefileid 或 .pdf 的链接
    if not pdfs:
        all_links = re.findall(r'<a[^>]*href="([^"]*)"[^>]*download="([^"]*)"[^>]*>', html)
        for href, filename in all_links:
            if 'imagefileid=' in href or href.lower().endswith('.pdf'):
                pdfs.append({'url': href, 'filename': filename})

    # 方法3: 更宽泛的PDF链接匹配
    if not pdfs:
        all_links = re.findall(r'<a[^>]*href="([^"]*\.pdf)"[^>]*>(.*?)</a>', html, re.DOTALL)
        for href, raw_text in all_links:
            text = re.sub(r'<[^>]+>', '', raw_text).strip()
            filename = text if text else href.split('/')[-1]
            pdfs.append({'url': href, 'filename': filename})

        if not pdfs:
            # 检查 imagefileid 类型的链接
            img_links = re.findall(r'<a[^>]*href="([^"]*imagefileid=[^"]*)"[^>]*>(.*?)</a>', html, re.DOTALL)
            for href, raw_text in img_links:
                text = re.sub(r'<[^>]+>', '', raw_text).strip()
                filename = text if text else href.split('/')[-1].split('?')[0]
                if not filename.endswith('.pdf'):
                    filename += '.pdf'
                pdfs.append({'url': href, 'filename': filename})

    return pdfs


def download_pdf(pdf_url, save_path):
    """下载PDF文件"""
    if save_path.exists():
        return save_path.stat().st_size

    # 确保完整URL
    if not pdf_url.startswith('http'):
        if pdf_url.startswith('//'):
            pdf_url = 'https:' + pdf_url
        elif pdf_url.startswith('/'):
            pdf_url = BASE_URL + pdf_url
        else:
            pdf_url = BASE_URL + '/' + pdf_url

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(pdf_url, stream=True, timeout=DOWNLOAD_TIMEOUT)
            if r.status_code == 200:
                save_path.parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                size = save_path.stat().st_size
                if size > 1000:  # 有效PDF至少1KB
                    return size
                save_path.unlink()
                return 0
            elif r.status_code == 404:
                return 0
        except Exception as e:
            if attempt >= MAX_RETRIES:
                return -1
            time.sleep(2 ** attempt)
    return -1


def is_2026(title, date_str=""):
    """判断是否为2026年预算"""
    if '2026' in title:
        return True
    if date_str and '2026' in date_str:
        return True
    return False


def crawl_department(dept, state):
    """爬取单个部门的所有2026年预算PDF"""
    name = dept['name']
    code = dept['code']
    print(f"\n{'='*60}")
    print(f"[部门] {name}")
    print(f"[code] {code}")

    if name in state['completed']:
        print(f"  [跳过] 已完成")
        return

    page_no = 0
    total_articles = 0
    pdf_count = 0
    dept_completed = True

    while True:
        time.sleep(random.uniform(*REQUEST_DELAY))

        articles, total_pages = parse_list_page(code, page_no)
        if not articles:
            print(f"  第{page_no+1}页无文章，停止")
            break

        if page_no == 0:
            print(f"  总页数: {total_pages}")

        for article in articles:
            title = article['title']

            if not is_2026(title, article.get('date', '')):
                continue

            total_articles += 1
            print(f"  [2026] {title}")

            time.sleep(random.uniform(*REQUEST_DELAY))
            pdfs = parse_detail_page(article['url'])

            if not pdfs:
                print(f"    无PDF附件")
                continue

            # 创建子目录
            dept_dir = OUTPUT_ROOT / name
            dept_dir.mkdir(parents=True, exist_ok=True)

            for pdf_info in pdfs:
                pdf_count += 1
                filename = sanitize(pdf_info['filename'])
                if not filename.lower().endswith('.pdf'):
                    filename += '.pdf'
                save_path = dept_dir / filename

                size = download_pdf(pdf_info['url'], save_path)
                if size > 0:
                    print(f"    PDF OK: {filename} ({size/1024:.0f}KB)")
                    state['stats']['total_pdfs'] += 1
                    state['stats']['total_size'] += size
                elif size == 0:
                    print(f"    PDF FAIL(404/empty): {filename}")
                    dept_completed = False
                else:
                    print(f"    PDF FAIL(download): {filename}")
                    dept_completed = False

        page_no += 1
        if total_pages and page_no >= total_pages:
            break

    if dept_completed:
        state['completed'].append(name)
    else:
        state['failed'][name] = f"部分PDF下载失败"
    save_state(state)

    print(f"  完成: {total_articles}篇2026文章, {pdf_count}个PDF")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="徐汇区部门预算PDF爬虫")
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不下载')
    parser.add_argument('--test', type=int, default=0, help='测试前N个部门')
    parser.add_argument('--dept', type=str, default='', help='只爬取指定部门(名称关键词)')
    args = parser.parse_args()

    depts = load_departments()
    print(f"加载到 {len(depts)} 个部门")

    state = load_state()
    print(f"已完成: {len(state['completed'])} 个部门")
    print(f"已下载: {state['stats']['total_pdfs']} 个PDF")

    if args.dept:
        depts = [d for d in depts if args.dept in d['name']]
        print(f"筛选后: {len(depts)} 个部门")

    if args.test:
        depts = depts[:args.test]
        print(f"测试模式: 前 {len(depts)} 个部门")

    if args.dry_run:
        # 仅预览：列出各部门的文章数
        for d in depts[:10]:
            if d['name'] in state['completed']:
                print(f"  {d['name']}: [已完成]")
                continue
            time.sleep(random.uniform(*REQUEST_DELAY))
            articles, total_pages = parse_list_page(d['code'], 0)
            count_2026 = sum(1 for a in articles if is_2026(a['title'], a.get('date', '')))
            print(f"  {d['name']}: {len(articles)}篇文章({count_2026}篇2026), {total_pages}页")
        return

    for i, dept in enumerate(depts):
        print(f"\n[{i+1}/{len(depts)}]", end="")
        try:
            crawl_department(dept, state)
        except Exception as e:
            print(f"  [ERROR] {e}")
            state['failed'][dept['name']] = str(e)
            save_state(state)

    print(f"\n{'='*60}")
    print(f"全部完成！")
    print(f"  完成部门: {len(state['completed'])}")
    print(f"  失败部门: {len(state['failed'])}")
    print(f"  总PDF: {state['stats']['total_pdfs']}")
    print(f"  总大小: {state['stats']['total_size']/1024/1024:.1f}MB")


if __name__ == '__main__':
    main()
