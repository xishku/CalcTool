#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
徐汇区教育局政务公开 - 教育、卫生计生系统预算 PDF 附件爬虫

功能：
- 访问列表页面，获取所有文章链接
- 遍历每篇文章详情页，提取PDF附件链接
- 下载PDF文件到指定目录
- 支持断点续传（避免重复下载）
- 记录下载日志和失败情况
- 保存元数据（标题、发布日期、来源URL等）
- 异常处理和重试机制
- 请求间隔控制（避免被封IP）
"""

import os
import re
import json
import time
import hashlib
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

# ============================================================================
# 配置
# ============================================================================

# 列表页基础 URL
BASE_URL = "https://www.xuhui.gov.cn"
LIST_URL = (
    "https://www.xuhui.gov.cn/xxgk/portal/article/list"
    "?menuType=wgk&code=xhxxgk_jyj_cz_czxx_jywsbmys"
)

# 输出目录
OUTPUT_DIR = Path(__file__).parent / "src"
PDF_DIR = OUTPUT_DIR / "pdf"
LOG_DIR = OUTPUT_DIR / "logs"
METADATA_FILE = OUTPUT_DIR / "metadata.json"

# 请求配置
REQUEST_INTERVAL = (1.0, 2.5)       # 随机请求间隔（秒）
MAX_RETRIES = 3                      # 最大重试次数
RETRY_BACKOFF_FACTOR = 2            # 退避因子
REQUEST_TIMEOUT = 60                 # 请求超时（秒）
DOWNLOAD_TIMEOUT = 120               # PDF下载超时（秒）

# 自定义请求头
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
}

# 日志配置
LOG_FILE = LOG_DIR / "crawler.log"

# ============================================================================
# 初始化
# ============================================================================


def setup_logging():
    """配置日志系统"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger(__name__)


logger = setup_logging()


# ============================================================================
# 元数据管理（断点续传支持）
# ============================================================================


class MetadataManager:
    """管理已下载文件的元数据，支持断点续传"""

    def __init__(self, metadata_file: Path):
        self.metadata_file = metadata_file
        self.data = self._load()

    def _load(self) -> dict:
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("元数据文件损坏，将重新创建: %s", e)
        return {
            "source_url": LIST_URL,
            "created_at": datetime.now().isoformat(),
            "articles": {},      # key: article_id
            "stats": {
                "total_pdfs": 0,
                "total_size": 0,
                "success_count": 0,
                "fail_count": 0,
                "skip_count": 0,
            },
        }

    def save(self):
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def is_article_processed(self, article_id: str) -> bool:
        return article_id in self.data["articles"]

    def is_pdf_downloaded(self, article_id: str, pdf_url: str) -> bool:
        article = self.data["articles"].get(article_id, {})
        for pdf_info in article.get("pdfs", []):
            if pdf_info["pdf_url"] == pdf_url and pdf_info.get("status") == "success":
                local_path = Path(pdf_info["local_path"])
                if local_path.exists():
                    return True
        return False

    def mark_downloaded(
        self,
        article_id: str,
        article_title: str,
        article_url: str,
        publish_date: str,
        pdf_url: str,
        pdf_filename: str,
        local_path: str,
        file_size: int,
    ):
        if article_id not in self.data["articles"]:
            self.data["articles"][article_id] = {
                "article_title": article_title,
                "article_url": article_url,
                "publish_date": publish_date,
                "pdfs": [],
            }

        self.data["articles"][article_id]["pdfs"].append({
            "pdf_url": pdf_url,
            "pdf_filename": pdf_filename,
            "local_path": local_path,
            "file_size": file_size,
            "download_date": datetime.now().isoformat(),
            "status": "success",
        })

        self.data["stats"]["success_count"] += 1
        self.data["stats"]["total_pdfs"] += 1
        self.data["stats"]["total_size"] += file_size
        self.save()

    def mark_failed(
        self,
        article_id: str,
        article_title: str,
        article_url: str,
        publish_date: str,
        pdf_url: str,
        error: str,
    ):
        if article_id not in self.data["articles"]:
            self.data["articles"][article_id] = {
                "article_title": article_title,
                "article_url": article_url,
                "publish_date": publish_date,
                "pdfs": [],
            }

        self.data["articles"][article_id]["pdfs"].append({
            "pdf_url": pdf_url,
            "download_date": datetime.now().isoformat(),
            "status": "failed",
            "error": error,
        })

        self.data["stats"]["fail_count"] += 1
        self.save()

    def mark_skip(self, article_id: str):
        """标记跳过的文章"""
        if article_id not in self.data["articles"]:
            self.data["articles"][article_id] = {
                "article_title": "(skipped - no PDF)",
                "article_url": "",
                "publish_date": "",
                "pdfs": [],
            }
        self.data["stats"]["skip_count"] += 1
        self.save()


# ============================================================================
# HTTP 请求工具
# ============================================================================


class HttpClient:
    """带重试和限速的 HTTP 客户端"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _respect_rate_limit(self):
        """随机休眠以控制请求频率"""
        delay = random.uniform(*REQUEST_INTERVAL)
        time.sleep(delay)

    def get(self, url: str, timeout: int = REQUEST_TIMEOUT) -> requests.Response:
        """GET 请求（带重试）"""
        self._respect_rate_limit()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.debug("GET %s (第%d次尝试)", url, attempt)
                resp = self.session.get(url, timeout=timeout)
                resp.raise_for_status()
                resp.encoding = resp.apparent_encoding or "utf-8"
                return resp
            except requests.RequestException as e:
                logger.warning("请求失败 [%s] 第%d次尝试: %s", url, attempt, e)
                if attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF_FACTOR ** attempt + random.uniform(0, 1)
                    logger.info("等待 %.1f 秒后重试...", wait)
                    time.sleep(wait)
                else:
                    raise

    def download(
        self, url: str, save_path: Path, timeout: int = DOWNLOAD_TIMEOUT
    ) -> bool:
        """流式下载文件（带重试）"""
        self._respect_rate_limit()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.debug("下载: %s (第%d次尝试)", url, attempt)
                resp = self.session.get(url, stream=True, timeout=timeout)
                resp.raise_for_status()

                with open(save_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                logger.debug("下载完成: %s", save_path.name)
                return True
            except requests.RequestException as e:
                logger.warning("下载失败 [%s] 第%d次尝试: %s", url, attempt, e)
                if attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF_FACTOR ** attempt + random.uniform(0, 1)
                    logger.info("等待 %.1f 秒后重试...", wait)
                    time.sleep(wait)

        return False


# ============================================================================
# 爬虫核心
# ============================================================================


class XuhuiBudgetCrawler:
    """徐汇区教育局预算 PDF 爬虫"""

    def __init__(self):
        self.http = HttpClient()
        self.meta = MetadataManager(METADATA_FILE)
        logger.info("爬虫已初始化，输出目录: %s", OUTPUT_DIR)

    def parse_list_page(self, page_no: int) -> list[dict]:
        """
        解析列表页，提取文章列表。

        Returns:
            list[dict]: 文章列表 [{id, title, date, url}, ...]
        """
        url = f"{LIST_URL}&page={page_no}"
        logger.info("正在解析列表页第%d页: %s", page_no + 1, url)

        resp = self.http.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        articles = []
        table = soup.find("table", class_="table")
        if not table:
            logger.warning("第%d页未找到表格", page_no + 1)
            return articles

        rows = table.find_all("tr")[1:]  # 跳过表头
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 3:
                continue

            # 提取标题链接
            title_a = cells[0].find("a", class_="li_title")
            if not title_a:
                continue

            title = title_a.get_text(strip=True)
            href = title_a.get("href", "")

            # 提取文章 ID
            article_id = None
            if "id=" in href:
                article_id = href.split("id=")[-1]

            # 提取发布日期
            date_text = ""
            date_a = cells[1].find("a")
            if date_a:
                date_text = date_a.get_text(strip=True)

            article_url = f"{BASE_URL}{href}" if href.startswith("/") else href

            articles.append({
                "id": article_id,
                "title": title,
                "date": date_text,
                "url": article_url,
            })

        logger.info("第%d页解析完成，找到 %d 篇文章", page_no + 1, len(articles))
        return articles

    def get_total_page_count(self) -> int:
        """获取总页数"""
        url = f"{LIST_URL}&page=0"
        resp = self.http.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        total_elem = soup.find("b", class_="total")
        if total_elem:
            text = total_elem.get_text(strip=True)
            # "共66页 1311条记录"
            match = re.search(r"共(\d+)页", text)
            if match:
                return int(match.group(1))

        logger.warning("无法获取总页数，使用默认值66")
        return 66

    def parse_detail_page(self, article: dict) -> dict:
        """
        解析详情页，提取元数据和 PDF 附件链接。

        Returns:
            dict: {pdf_url, pdf_filename, publish_date, publisher, ...}
        """
        logger.info("正在解析详情页: %s", article["title"])
        resp = self.http.get(article["url"])
        soup = BeautifulSoup(resp.text, "html.parser")

        result = {
            "article_id": article["id"],
            "article_title": article["title"],
            "article_url": article["url"],
            "publish_date": article.get("date", ""),
            "publisher": "",
            "pdfs": [],
        }

        # 提取元数据
        # 标题
        meta_title = soup.find("meta", attrs={"name": "ArticleTitle"})
        if meta_title:
            result["article_title"] = meta_title.get("content", article["title"])

        # 发布日期
        meta_date = soup.find("meta", attrs={"name": "PubDate"})
        if meta_date:
            result["publish_date"] = meta_date.get("content", article.get("date", ""))

        # 如果 meta 中没有日期，尝试从页面文本中提取
        if not result["publish_date"]:
            publish_p = soup.find(string=re.compile(r"发布时间"))
            if publish_p:
                date_match = re.search(r"(\d{4}-\d{2}-\d{2})", publish_p)
                if date_match:
                    result["publish_date"] = date_match.group(1)

        # 发布机构
        pub_org = soup.find("span", string=re.compile(r"发布机构"))
        if pub_org:
            result["publisher"] = pub_org.get_text(strip=True).replace("发布机构 : ", "")

        # 提取 PDF 附件
        attachment_div = soup.find("div", class_="attachment_part")
        if attachment_div:
            pdf_links = attachment_div.find_all("a")
            for link in pdf_links:
                href = link.get("href", "")
                if "imagefileid=" in href or href.lower().endswith(".pdf"):
                    filename = link.get("download") or link.get_text(strip=True)
                    if not filename or "." not in filename:
                        filename = f"{result['article_title']}.pdf"

                    # 清理文件名中的非法字符
                    filename = self._sanitize_filename(filename)

                    result["pdfs"].append({
                        "pdf_url": href,
                        "pdf_filename": filename,
                    })

        pdf_count = len(result["pdfs"])
        logger.info(
            "详情页解析完成: %s, 找到 %d 个PDF",
            result["article_title"],
            pdf_count,
        )
        return result

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """清理文件名中的非法字符"""
        # 移除 Windows 文件名不允许的字符
        illegal_chars = r'[<>:"/\\|?*]'
        filename = re.sub(illegal_chars, "_", filename)
        # 限制长度
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[: 200 - len(ext)] + ext
        return filename

    def download_pdf(self, pdf_info: dict, article: dict) -> bool:
        """
        下载一个 PDF 文件。

        Returns:
            bool: 下载是否成功
        """
        pdf_url = pdf_info["pdf_url"]
        filename = pdf_info["pdf_filename"]
        save_path = PDF_DIR / filename

        # 断点续传检查
        if save_path.exists():
            file_size = save_path.stat().st_size
            if file_size > 0:
                logger.info("文件已存在，跳过: %s (%.1f KB)", filename, file_size / 1024)
                self.meta.mark_downloaded(
                    article_id=article["article_id"],
                    article_title=article["article_title"],
                    article_url=article["article_url"],
                    publish_date=article["publish_date"],
                    pdf_url=pdf_url,
                    pdf_filename=filename,
                    local_path=str(save_path),
                    file_size=file_size,
                )
                return True

        logger.info("正在下载: %s", filename)
        success = self.http.download(pdf_url, save_path)

        if success and save_path.exists():
            file_size = save_path.stat().st_size
            if file_size == 0:
                logger.warning("下载的文件为空: %s", filename)
                save_path.unlink()
                self.meta.mark_failed(
                    article_id=article["article_id"],
                    article_title=article["article_title"],
                    article_url=article["article_url"],
                    publish_date=article["publish_date"],
                    pdf_url=pdf_url,
                    error="文件为空",
                )
                return False

            logger.info("下载成功: %s (%.1f KB)", filename, file_size / 1024)
            self.meta.mark_downloaded(
                article_id=article["article_id"],
                article_title=article["article_title"],
                article_url=article["article_url"],
                publish_date=article["publish_date"],
                pdf_url=pdf_url,
                pdf_filename=filename,
                local_path=str(save_path),
                file_size=file_size,
            )
            return True
        else:
            logger.error("下载失败: %s", filename)
            self.meta.mark_failed(
                article_id=article["article_id"],
                article_title=article["article_title"],
                article_url=article["article_url"],
                publish_date=article["publish_date"],
                pdf_url=pdf_url,
                error="多次重试后下载失败",
            )
            return False

    def run(self, start_page: int = 0, max_pages: Optional[int] = None):
        """
        执行爬虫。

        Args:
            start_page: 起始页码（0-based）
            max_pages: 最大抓取页数，None 表示抓取所有页
        """
        logger.info("=" * 60)
        logger.info("爬虫开始运行")
        logger.info("列表URL: %s", LIST_URL)
        logger.info("输出目录: %s", PDF_DIR)
        logger.info("=" * 60)

        # 获取总页数
        total_pages = self.get_total_page_count()
        logger.info("总页数: %d", total_pages)

        if max_pages:
            total_pages = min(total_pages, start_page + max_pages)

        total_articles = 0
        total_pdfs = 0
        success_count = 0
        fail_count = 0
        skip_count = 0

        for page_no in range(start_page, total_pages):
            try:
                articles = self.parse_list_page(page_no)
            except Exception as e:
                logger.error("解析列表页第%d页失败: %s", page_no + 1, e)
                continue

            if not articles:
                logger.warning("第%d页没有文章，可能已到达最后一页", page_no + 1)
                break

            for article in articles:
                article_id = article["id"]
                if not article_id:
                    logger.warning("文章缺少ID，跳过: %s", article["title"])
                    continue

                # 断点续传：跳过已处理的文章
                if self.meta.is_article_processed(article_id):
                    logger.debug("文章已处理，跳过: %s", article["title"])
                    skip_count += 1
                    continue

                try:
                    detail = self.parse_detail_page(article)
                except Exception as e:
                    logger.error("解析详情页失败 [%s]: %s", article["title"], e)
                    fail_count += 1
                    continue

                total_articles += 1

                if not detail["pdfs"]:
                    logger.info("文章无PDF附件，跳过: %s", detail["article_title"])
                    self.meta.mark_skip(article_id)
                    skip_count += 1
                    continue

                for pdf_info in detail["pdfs"]:
                    total_pdfs += 1
                    try:
                        if self.download_pdf(pdf_info, detail):
                            success_count += 1
                        else:
                            fail_count += 1
                    except Exception as e:
                        logger.error("下载PDF异常 [%s]: %s", pdf_info["pdf_filename"], e)
                        fail_count += 1

            # 每页完成后输出进度
            logger.info(
                "进度: 第%d/%d页完成, 累计文章:%d, PDF:%d, 成功:%d, 失败:%d, 跳过:%d",
                page_no + 1,
                total_pages,
                total_articles,
                total_pdfs,
                success_count,
                fail_count,
                skip_count,
            )

        # 最终报告
        logger.info("=" * 60)
        logger.info("爬虫运行完成！")
        logger.info("总计文章数: %d", total_articles)
        logger.info("总计PDF数: %d", total_pdfs)
        logger.info("下载成功: %d", success_count)
        logger.info("下载失败: %d", fail_count)
        logger.info("跳过/无PDF: %d", skip_count)
        logger.info("元数据文件: %s", METADATA_FILE)
        logger.info("=" * 60)

        return {
            "total_articles": total_articles,
            "total_pdfs": total_pdfs,
            "success_count": success_count,
            "fail_count": fail_count,
            "skip_count": skip_count,
        }


# ============================================================================
# 入口
# ============================================================================


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="徐汇区教育局预算PDF爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python crawler.py                  # 爬取全部页面
  python crawler.py -s 10 -n 5       # 从第10页开始，爬取5页
  python crawler.py --test 1         # 测试模式：只爬取第1页
        """,
    )
    parser.add_argument(
        "-s", "--start-page", type=int, default=0,
        help="起始页码（0-based，默认0）",
    )
    parser.add_argument(
        "-n", "--num-pages", type=int, default=None,
        help="抓取页数（默认全部）",
    )
    parser.add_argument(
        "--test", type=int, default=None,
        help="测试模式：只抓取指定页数（等同于 -s 0 -n N）",
    )

    args = parser.parse_args()

    start_page = args.start_page
    num_pages = args.num_pages

    if args.test is not None:
        start_page = 0
        num_pages = args.test
        logger.info("*** 测试模式：只抓取前 %d 页 ***", num_pages)

    crawler = XuhuiBudgetCrawler()
    crawler.run(start_page=start_page, max_pages=num_pages)


if __name__ == "__main__":
    main()
