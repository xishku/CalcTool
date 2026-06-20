#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统计分析脚本 - 对爬取的PDF进行统计并生成报告

功能：
- 统计PDF数量和总大小
- 按时间分布统计
- 按发布机构统计
- 列出下载失败项
- 生成 Markdown / 文本 格式的统计报告
"""

import json
import os
from datetime import datetime
from collections import defaultdict, Counter
from pathlib import Path

# ============================================================================
# 配置
# ============================================================================

SCRIPT_DIR = Path(__file__).parent
SRC_DIR = SCRIPT_DIR / "src"
METADATA_FILE = SRC_DIR / "metadata.json"
REPORT_FILE = SRC_DIR / "report.md"


# ============================================================================
# 工具函数
# ============================================================================


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def parse_date(date_str: str) -> str:
    """解析日期字符串，返回标准格式 YYYY-MM"""
    if not date_str:
        return "未知"
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return dt.strftime("%Y-%m")
    except ValueError:
        return date_str[:7] if len(date_str) >= 7 else "未知"


# ============================================================================
# 统计分析类
# ============================================================================


class PDFStats:
    """PDF 统计分析器"""

    def __init__(self, metadata_file: Path):
        self.metadata_file = metadata_file
        self.data = self._load()
        self.report_lines = []

    def _load(self) -> dict:
        if not self.metadata_file.exists():
            print(f"错误: 元数据文件不存在: {self.metadata_file}")
            print("请先运行 crawler.py 爬取数据")
            exit(1)

        with open(self.metadata_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _h(self, text: str, level: int = 1):
        """添加标题到报告"""
        self.report_lines.append(f"{'#' * level} {text}")
        self.report_lines.append("")

    def _line(self, text: str = ""):
        """添加一行到报告"""
        self.report_lines.append(text)

    def _table_header(self, headers: list):
        """添加表格头"""
        self.report_lines.append("| " + " | ".join(headers) + " |")
        self.report_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    def _table_row(self, cells: list):
        """添加表格行"""
        self.report_lines.append("| " + " | ".join(str(c) for c in cells) + " |")

    def analyze(self):
        """执行全部分析"""
        self._h("徐汇区教育局预算 PDF 统计报告", 1)
        self._line(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._line(f"> 数据来源: {self.data.get('source_url', 'N/A')}")
        self._line(f"> 爬取时间: {self.data.get('created_at', 'N/A')}")
        self._line()

        self._count_overview()
        self._size_analysis()
        self._time_distribution()
        self._publisher_distribution()
        self._list_failures()
        self._list_top_files()

        return "\n".join(self.report_lines)

    def _collect_pdf_records(self):
        """收集所有成功的 PDF 记录"""
        records = []
        for article_id, article in self.data.get("articles", {}).items():
            for pdf in article.get("pdfs", []):
                if pdf.get("status") == "success":
                    records.append({
                        "article_id": article_id,
                        "article_title": article.get("article_title", ""),
                        "publish_date": article.get("publish_date", ""),
                        "pdf_filename": pdf.get("pdf_filename", ""),
                        "local_path": pdf.get("local_path", ""),
                        "file_size": pdf.get("file_size", 0),
                        "download_date": pdf.get("download_date", ""),
                    })
        return records

    def _count_overview(self):
        """总览统计"""
        self._h("一、总览", 2)

        stats = self.data.get("stats", {})
        valid_records = self._collect_pdf_records()
        failed_pdfs = self._collect_failures()

        self._table_header(["指标", "数值"])
        self._table_row(["文章总数", len(self.data.get("articles", {}))])
        self._table_row(["成功下载的PDF总数", len(valid_records)])
        self._table_row(["下载失败的PDF数", len(failed_pdfs)])
        self._table_row(["跟踪的成功数", stats.get("success_count", 0)])
        self._table_row(["跟踪的失败数", stats.get("fail_count", 0)])
        self._table_row(["跳过的文章数", stats.get("skip_count", 0)])
        self._table_row(["PDF总大小", format_size(stats.get("total_size", 0))])

        # 校验
        if len(valid_records) != stats.get("success_count", 0):
            self._line()
            self._line(
                f"> ⚠️ 注意: 实际文件数({len(valid_records)}) "
                f"与记录数({stats.get('success_count', 0)})不一致，"
                f"可能有文件被手动删除"
            )

        self._line()

    def _size_analysis(self):
        """文件大小分析"""
        self._h("二、文件大小分析", 2)

        records = self._collect_pdf_records()
        if not records:
            self._line("暂无数据")
            self._line()
            return

        sizes = [r["file_size"] for r in records]
        sizes.sort()

        total_size = sum(sizes)
        avg_size = total_size / len(sizes)
        min_size = min(sizes)
        max_size = max(sizes)
        median_size = sizes[len(sizes) // 2]

        self._table_header(["指标", "数值"])
        self._table_row(["总大小", format_size(total_size)])
        self._table_row(["平均大小", format_size(int(avg_size))])
        self._table_row(["中位数大小", format_size(median_size)])
        self._table_row(["最小文件", format_size(min_size)])
        self._table_row(["最大文件", format_size(max_size)])

        # 大小分布
        size_ranges = {
            "<100KB": (0, 102400),
            "100KB-500KB": (102400, 512000),
            "500KB-1MB": (512000, 1048576),
            "1MB-5MB": (1048576, 5242880),
            "5MB-10MB": (5242880, 10485760),
            ">10MB": (10485760, float("inf")),
        }

        self._line()
        self._h("大小分布", 3)
        self._table_header(["范围", "数量", "占比"])
        for label, (lo, hi) in size_ranges.items():
            count = sum(1 for s in sizes if lo <= s < hi)
            pct = f"{count / len(sizes) * 100:.1f}%" if count > 0 else "0%"
            self._table_row([label, count, pct])

        self._line()

    def _time_distribution(self):
        """按时间分布统计"""
        self._h("三、时间分布", 2)

        records = self._collect_pdf_records()
        if not records:
            self._line("暂无数据")
            self._line()
            return

        # 按年-月统计
        month_counter = Counter()
        year_counter = Counter()
        for r in records:
            date_key = parse_date(r.get("publish_date", ""))
            month_counter[date_key] += 1
            if date_key != "未知" and "-" in date_key:
                year_counter[date_key[:4]] += 1

        # 按年份
        self._h("按年份", 3)
        if year_counter:
            self._table_header(["年份", "PDF数量", "占比"])
            total = sum(year_counter.values())
            for year in sorted(year_counter.keys()):
                count = year_counter[year]
                self._table_row([year, count, f"{count / total * 100:.1f}%"])
        else:
            self._line("暂无按年份的数据")

        # 按月份
        self._line()
        self._h("按月分布（近12个月）", 3)
        if month_counter:
            self._table_header(["月份", "PDF数量"])
            for month in sorted(month_counter.keys(), reverse=True)[:12]:
                self._table_row([month, month_counter[month]])
        else:
            self._line("暂无按月份的数据")

        self._line()

    def _publisher_distribution(self):
        """按发布机构统计"""
        self._h("四、发布机构统计", 2)

        publisher_counter = Counter()
        for article_id, article in self.data.get("articles", {}).items():
            publisher = article.get("publisher", "")
            if not publisher:
                # 尝试从文章标题推断
                title = article.get("article_title", "")
                if title:
                    publisher = "未标注（页面中提取）"
            publisher_counter[publisher or "未知"] += 1

        if publisher_counter:
            self._table_header(["发布机构", "文章数量"])
            for pub, count in publisher_counter.most_common():
                self._table_row([pub, count])
        else:
            self._line("暂无发布机构数据")

        self._line()

    def _collect_failures(self):
        """收集失败的PDF"""
        failures = []
        for article_id, article in self.data.get("articles", {}).items():
            for pdf in article.get("pdfs", []):
                if pdf.get("status") == "failed":
                    failures.append({
                        "article_id": article_id,
                        "article_title": article.get("article_title", ""),
                        "pdf_url": pdf.get("pdf_url", ""),
                        "error": pdf.get("error", "未知错误"),
                    })
        return failures

    def _list_failures(self):
        """列出失败项"""
        self._h("五、下载失败记录", 2)

        failures = self._collect_failures()
        if not failures:
            self._line("✅ 所有PDF均下载成功！")
            self._line()
            return

        self._table_header(["文章标题", "错误信息"])
        for f in failures:
            title = f["article_title"][:40] + (
                "..." if len(f["article_title"]) > 40 else ""
            )
            error = f["error"][:50] + ("..." if len(f["error"]) > 50 else "")
            self._table_row([title, error])

        self._line()

    def _list_top_files(self):
        """列出最大的文件"""
        self._h("六、最大的10个PDF文件", 2)

        records = self._collect_pdf_records()
        if not records:
            self._line("暂无数据")
            self._line()
            return

        records.sort(key=lambda r: r["file_size"], reverse=True)
        top10 = records[:10]

        self._table_header(["文件名", "大小"])
        for r in top10:
            name = r["pdf_filename"][:50] + (
                "..." if len(r["pdf_filename"]) > 50 else ""
            )
            self._table_row([name, format_size(r["file_size"])])

        self._line()

    def save_report(self, output_path: Path = None):
        """保存报告到文件"""
        if output_path is None:
            output_path = REPORT_FILE

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self.report)

        print(f"统计报告已保存到: {output_path}")

    @property
    def report(self):
        return "\n".join(self.report_lines)


# ============================================================================
# 入口
# ============================================================================


def main():
    import argparse

    parser = argparse.ArgumentParser(description="PDF统计报告生成工具")
    parser.add_argument(
        "-o", "--output", type=str, default=None,
        help="输出文件路径（默认: src/report.md）",
    )
    parser.add_argument(
        "-m", "--metadata", type=str, default=None,
        help="元数据文件路径（默认: src/metadata.json）",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="同时输出 JSON 格式的统计摘要",
    )

    args = parser.parse_args()

    metadata_file = Path(args.metadata) if args.metadata else METADATA_FILE
    output_path = Path(args.output) if args.output else REPORT_FILE

    stats = PDFStats(metadata_file)
    report = stats.analyze()

    # 打印报告
    print(report)

    # 保存报告
    stats.save_report(output_path)

    # 可选 JSON 输出
    if args.json:
        json_output = output_path.with_suffix(".json")
        records = stats._collect_pdf_records()
        json_data = {
            "generated_at": datetime.now().isoformat(),
            "total_pdfs": len(records),
            "total_size": sum(r["file_size"] for r in records),
            "total_size_formatted": format_size(
                sum(r["file_size"] for r in records)
            ),
            "failures": len(stats._collect_failures()),
            "records": records,
        }
        with open(json_output, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        print(f"JSON摘要已保存到: {json_output}")


if __name__ == "__main__":
    main()
