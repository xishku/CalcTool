#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
徐汇区教育局各单位预算 - 财政拨款收入分析

功能：
- 遍历所有已下载的预算 PDF，提取财政拨款收入及其组成数据
- 按年份汇总统计：财政拨款收入、一般公共预算、政府性基金、国有资本经营预算
- 按单位统计各年数据
- 生成 Markdown 报告和 JSON 数据文件

数据提取策略：
1. 优先从第6页"预算编制说明"文本中提取（单位：万元）
2. 文本解析失败时，从第7页"财务收支预算总表"表格中提取（单位：元，转换为万元）
"""

import os
import re
import json
import logging
from collections import defaultdict
from pathlib import Path
from datetime import datetime

import pdfplumber

# ============================================================================
# 配置
# ============================================================================

SCRIPT_DIR = Path(__file__).parent
PDF_DIR = SCRIPT_DIR / "src" / "pdf"
OUTPUT_DIR = SCRIPT_DIR / "src"
BUDGET_DATA_FILE = OUTPUT_DIR / "budget_data.json"
REPORT_FILE = OUTPUT_DIR / "budget_report.md"
LOG_FILE = OUTPUT_DIR / "logs" / "budget_analyzer.log"

MIN_PDF_SIZE = 5000  # 小于5KB的文件视为无效占位文件

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ============================================================================
# 核心：PDF 解析
# ============================================================================


def find_budget_text_page(pdf: pdfplumber.PDF) -> int | None:
    """
    查找包含预算编制说明的页码（0-indexed）。
    搜索特征：同时包含"收入预算"和"财政拨款收入"且带数字。
    """
    for i, page in enumerate(pdf.pages):
        text = page.extract_text()
        if not text:
            continue
        # 搜索包含"财政拨款收入"+数字的页面（即预算编制说明页）
        # 排除"非同级财政拨款收入"避免误匹配
        if re.search(r"(?<!非同级)财政拨款收入?\s*[\d,]+\.?\d*", text):
            return i
    return None


def extract_from_text(page_text: str) -> dict | None:
    """
    从预算编制说明文本中提取财政拨款数据（万元）。
    
    文本结构（不同年份略有差异）：
      “收入预算X万元，其中：财政拨款收入X万元……”
      “支出预算X万元……财政拨款支出预算中，[一般公共预算/政府性基金/国有资本]明细……”
      或旧格式：
      “增加X万元。其中，一般公共预算拨款支出预算X万元……政府性基金拨款支出预算X万元……”
    
    策略：合并跨行文本 → 正则提取财政拨款收入 → 在锚点后提取三项明细
    """
    # 合并所有行，消除换行导致的关键词拆分
    text = page_text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    result = {}

    # 1. 提取"财政拨款收入"（在收入预算段落中）
    #    注意：
    #    - 某些PDF中"万元"被跨行拆分为"万 元"
    #    - 某些PDF中"入"字在文本提取时丢失，变成"财政拨款收"
    #    - 必须排除"非同级财政拨款收入"（避免误匹配）
    m = re.search(r"(?<!非同级)财政拨款收入?\s*([\d,]+\.?\d*)\s*万\s*元", text)
    if not m:
        return None
    sr_val = float(m.group(1).replace(",", ""))
    
    # 如果提取到0，尝试用"财政拨款收"（缺失入）重新提取
    # 这种情况发生在PDF文本提取丢失"入"字时
    if sr_val == 0:
        m2 = re.search(r"(?<!非同级)财政拨款收\s*([\d,]+\.?\d*)\s*万\s*元", text)
        if m2:
            sr_val2 = float(m2.group(1).replace(",", ""))
            if sr_val2 > 0:
                sr_val = sr_val2
    result["财政拨款收入"] = sr_val

    # 2. 找到三项明细的起始锚点
    #    2026格式: "财政拨款支出预算中，..."
    #    2022-2025格式: "。其中，一般公共预算拨款支出预算..."
    three_items = {}
    for anchor in ["财政拨款支出预算中", "。其中，"]:
        idx = text.find(anchor)
        if idx >= 0:
            # 截取锚点之后的部分
            section = text[idx + len(anchor):]
            # 提取所有"拨款支出预算N万元"模式（这是三项明细的通用后缀）
            # 注意：PDF跨行拆分极其随机，每个汉字之间都可能插入空格
            # "拨款支出预算" 可能被拆分为 "拨 款 支 出 预 算" 的任意子集
            numbers = re.findall(r"拨\s*款\s*支\s*出\s*预\s*算\s*([\d,]+\.?\d*)\s*万\s*元", section)
            if numbers:
                try:
                    three_items["一般公共预算"] = float(numbers[0].replace(",", ""))
                except ValueError:
                    pass
                if len(numbers) > 1:
                    try:
                        three_items["政府性基金"] = float(numbers[1].replace(",", ""))
                    except ValueError:
                        pass
                if len(numbers) > 2:
                    try:
                        three_items["国有资本经营预算"] = float(numbers[2].replace(",", ""))
                    except ValueError:
                        pass
            break  # 找到第一个锚点就停止

    # 填充结果
    result["一般公共预算"] = three_items.get("一般公共预算")
    result["政府性基金"] = three_items.get("政府性基金")
    result["国有资本经营预算"] = three_items.get("国有资本经营预算")

    # 3. 后备方案：用独立正则兜底（每个汉字都容忍空格拆分）
    fallback_patterns = {
        "一般公共预算": [
            r"一般\s*公共\s*预\s*算\s*拨\s*款\s*支\s*出\s*预\s*算\s*([\d,]+\.?\d*)\s*万\s*元",
            r"一般\s*公共\s*预\s*算[^。]*?([\d,]+\.?\d*)\s*万\s*元",
        ],
        "政府性基金": [
            r"政府性\s*基金\s*拨\s*款\s*支\s*出\s*预\s*算\s*([\d,]+\.?\d*)\s*万\s*元",
        ],
        "国有资本经营预算": [
            r"国有\s*资本\s*经营\s*预\s*算\s*拨\s*款\s*支\s*出\s*预\s*算\s*([\d,]+\.?\d*)\s*万\s*元",
        ],
    }
    for key, pats in fallback_patterns.items():
        if result.get(key) is None:
            for pat in pats:
                m = re.search(pat, text)
                if m:
                    try:
                        result[key] = float(m.group(1).replace(",", ""))
                    except ValueError:
                        pass
                    break

    # 4. 最终兜底：如果一般公共预算缺失但其他两项都是0，推断=财政拨款收入
    if result.get("一般公共预算") is None:
        gf_val = result.get("政府性基金")
        gc_val = result.get("国有资本经营预算")
        if (gf_val is not None and gf_val == 0) and (gc_val is not None and gc_val == 0):
            result["一般公共预算"] = result.get("财政拨款收入")

    # 填充缺失的项为None（后续会转为0）
    for key in ["一般公共预算", "政府性基金", "国有资本经营预算"]:
        if key not in result:
            result[key] = None

    return result


def extract_from_table(pdf: pdfplumber.PDF) -> dict | None:
    """
    从"财务收支预算总表"表格中提取数据（单位：元）。
    作为文本解析失败时的后备方案。
    """
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if "财务收支预算总表" not in text:
            continue

        tables = page.extract_tables()
        if not tables:
            continue

        result = {}
        for table in tables:
            for row in table:
                if not row:
                    continue
                # row[0] is the item name, row[1] is the value
                first_cell = str(row[0]).strip() if row[0] else ""
                value_str = str(row[1]).replace(",", "").strip() if len(row) > 1 and row[1] else ""

                if "一、" in first_cell and "财政拨款收入" in first_cell:
                    try:
                        result["财政拨款收入"] = float(value_str) / 10000 if value_str else 0
                    except ValueError:
                        pass
                elif "1、一般公共预算" in first_cell or "1、" in first_cell and "般公共" in first_cell:
                    try:
                        result["一般公共预算"] = float(value_str) / 10000 if value_str else 0
                    except ValueError:
                        pass
                elif "2、政府性基金" in first_cell:
                    try:
                        result["政府性基金"] = float(value_str) / 10000 if value_str else 0
                    except ValueError:
                        pass
                elif "3、国有资本经营预算" in first_cell:
                    try:
                        result["国有资本经营预算"] = float(value_str) / 10000 if value_str else 0
                    except ValueError:
                        pass

        if result.get("财政拨款收入") is not None:
            logger.info("  使用表格数据（财务收支预算总表）")
            # 补全缺少的项为0
            for key in ["一般公共预算", "政府性基金", "国有资本经营预算"]:
                if key not in result or result[key] is None:
                    result[key] = 0.0
            return result

    return None


def parse_filename(filename: str) -> tuple[str | None, str | None]:
    """
    从文件名解析年份和单位名称。
    文件名格式: {编号}{学校名称}{YYYY}年度单位预算.pdf
    例如: 001上海市位育中学2026年度单位预算.pdf
    """
    # 去除扩展名
    name = Path(filename).stem

    # 提取年份
    year_match = re.search(r"(\d{4})年度", name)
    year = year_match.group(1) if year_match else None

    # 提取单位名称（去掉前导编号和年份）
    unit_match = re.match(r"\d+\s*(.+?)\s*\d{4}年度", name)
    unit = unit_match.group(1).strip() if unit_match else name

    return year, unit


# ============================================================================
# 主处理逻辑
# ============================================================================


def analyze_all_pdfs() -> list[dict]:
    """遍历所有PDF并提取预算数据"""
    if not PDF_DIR.exists():
        logger.error("PDF目录不存在: %s", PDF_DIR)
        return []

    pdf_files = sorted(f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf"))
    valid_count = 0
    skip_count = 0
    fail_count = 0
    results = []

    for f in pdf_files:
        filepath = PDF_DIR / f
        file_size = filepath.stat().st_size

        if file_size < MIN_PDF_SIZE:
            skip_count += 1
            continue

        year, unit = parse_filename(f)
        valid_count += 1

        logger.info("[%d/%d] 处理: %s (年份:%s)", valid_count, len(pdf_files), f, year)

        try:
            with pdfplumber.open(filepath) as pdf:
                # 步骤1：查找预算编制说明文本页
                text_page_idx = find_budget_text_page(pdf)

                data = None
                source = "unknown"

                # 步骤2：从文本提取
                if text_page_idx is not None:
                    page_text = pdf.pages[text_page_idx].extract_text()
                    data = extract_from_text(page_text)
                    if data:
                        source = "text"

                # 步骤3：后备方案 - 从表格提取
                if data is None:
                    data = extract_from_table(pdf)
                    if data:
                        source = "table"

                if data is None:
                    logger.warning("  >>> 未找到预算数据: %s", f)
                    fail_count += 1
                    results.append({
                        "file": f,
                        "year": year,
                        "unit": unit,
                        "status": "no_data",
                        "data": None,
                    })
                    continue

                # 转换为万元并保留2位小数
                record = {
                    "file": f,
                    "year": year,
                    "unit": unit,
                    "status": "ok",
                    "source": source,
                    "data": {k: round(v, 2) if v is not None else 0.0 for k, v in data.items()},
                }
                results.append(record)
                logger.info(
                    "  √ 财政拨款收入: %.2f万 | 一般公共预算: %.2f万 | "
                    "政府性基金: %.2f万 | 国有资本: %.2f万 [来源:%s]",
                    record["data"].get("财政拨款收入", 0),
                    record["data"].get("一般公共预算", 0),
                    record["data"].get("政府性基金", 0),
                    record["data"].get("国有资本经营预算", 0),
                    source,
                )

        except Exception as e:
            logger.error("  >>> 解析失败 [%s]: %s", f, e)
            fail_count += 1
            results.append({
                "file": f,
                "year": year,
                "unit": unit,
                "status": "error",
                "error": str(e),
            })

    logger.info("=" * 60)
    logger.info("分析完成：有效%d, 跳过(小文件)%d, 无数据/失败%d",
                sum(1 for r in results if r.get("status") == "ok"),
                skip_count,
                fail_count)
    return results


def save_data(results: list[dict]):
    """保存提取结果到JSON文件"""
    output = {
        "analyzed_at": datetime.now().isoformat(),
        "total_files": len(results),
        "success_count": sum(1 for r in results if r.get("status") == "ok"),
        "records": results,
    }
    with open(BUDGET_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    logger.info("数据已保存到: %s", BUDGET_DATA_FILE)


# ============================================================================
# 统计分析 & 报告生成
# ============================================================================


def generate_report(results: list[dict]):
    """生成年度汇总统计报告"""
    ok_records = [r for r in results if r.get("status") == "ok"]
    error_records = [r for r in results if r.get("status") != "ok"]

    # 按年份汇总
    year_summary: dict[str, dict] = defaultdict(lambda: {
        "count": 0,
        "财政拨款收入": 0.0,
        "一般公共预算": 0.0,
        "政府性基金": 0.0,
        "国有资本经营预算": 0.0,
        "units": [],
    })

    for r in ok_records:
        y = r.get("year", "未知")
        d = r.get("data", {})
        year_summary[y]["count"] += 1
        year_summary[y]["财政拨款收入"] += d.get("财政拨款收入", 0)
        year_summary[y]["一般公共预算"] += d.get("一般公共预算", 0)
        year_summary[y]["政府性基金"] += d.get("政府性基金", 0)
        year_summary[y]["国有资本经营预算"] += d.get("国有资本经营预算", 0)
        year_summary[y]["units"].append({
            "unit": r.get("unit"),
            **{k: d.get(k, 0) for k in ["财政拨款收入", "一般公共预算", "政府性基金", "国有资本经营预算"]},
        })

    # 生成 Markdown 报告
    lines = []
    lines.append("# 徐汇区教育局各单位预算 - 财政拨款收入分析报告")
    lines.append(f"\n> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"> 有效文件数：{len(ok_records)}")
    lines.append(f"> 无法解析文件数：{len(error_records)}")
    lines.append("")

    # 年度汇总表
    lines.append("## 一、年度汇总")
    lines.append("")
    lines.append("| 年份 | 单位数 | 财政拨款收入(万元) | 一般公共预算(万元) | 政府性基金(万元) | 国有资本经营预算(万元) |")
    lines.append("|------|--------|-------------------|-------------------|-----------------|----------------------|")

    grand_total = {"财政拨款收入": 0, "一般公共预算": 0, "政府性基金": 0, "国有资本经营预算": 0}
    total_units = 0

    for year in sorted(year_summary.keys()):
        s = year_summary[year]
        lines.append(
            f"| {year} | {s['count']} | "
            f"{s['财政拨款收入']:,.2f} | "
            f"{s['一般公共预算']:,.2f} | "
            f"{s['政府性基金']:,.2f} | "
            f"{s['国有资本经营预算']:,.2f} |"
        )
        for k in grand_total:
            grand_total[k] += s[k]
        total_units += s["count"]

    # 合计行
    lines.append(
        f"| **合计** | **{total_units}** | "
        f"**{grand_total['财政拨款收入']:,.2f}** | "
        f"**{grand_total['一般公共预算']:,.2f}** | "
        f"**{grand_total['政府性基金']:,.2f}** | "
        f"**{grand_total['国有资本经营预算']:,.2f}** |"
    )
    lines.append("")

    # 按单位详细列表
    lines.append("## 二、各单位明细")
    lines.append("")

    # 按年份和单位名排序
    sorted_records = sorted(ok_records, key=lambda r: (r.get("year", ""), r.get("unit", "")))

    current_year = None
    for r in sorted_records:
        y = r.get("year", "未知")
        if y != current_year:
            current_year = y
            lines.append(f"### {current_year}年度")
            lines.append("")
            lines.append("| 单位名称 | 财政拨款收入(万元) | 一般公共预算(万元) | 政府性基金(万元) | 国有资本(万元) |")
            lines.append("|----------|-------------------|-------------------|-----------------|---------------|")

        d = r.get("data", {})
        lines.append(
            f"| {r.get('unit', '-')} | "
            f"{d.get('财政拨款收入', 0):,.2f} | "
            f"{d.get('一般公共预算', 0):,.2f} | "
            f"{d.get('政府性基金', 0):,.2f} | "
            f"{d.get('国有资本经营预算', 0):,.2f} |"
        )

    lines.append("")

    # 非零政府性基金/国有资本的记录（重点关注）
    non_zero = [r for r in ok_records
                if r.get("data", {}).get("政府性基金", 0) > 0
                or r.get("data", {}).get("国有资本经营预算", 0) > 0]
    if non_zero:
        lines.append("## 三、非零政府性基金/国有资本经营预算记录")
        lines.append("")
        lines.append("| 年份 | 单位 | 政府性基金(万元) | 国有资本经营预算(万元) |")
        lines.append("|------|------|-----------------|----------------------|")
        for r in non_zero:
            d = r.get("data", {})
            lines.append(
                f"| {r.get('year')} | {r.get('unit')} | "
                f"{d.get('政府性基金', 0):,.2f} | "
                f"{d.get('国有资本经营预算', 0):,.2f} |"
            )
        lines.append("")
    else:
        lines.append("## 三、非零政府性基金/国有资本经营预算记录")
        lines.append("")
        lines.append("> 所有单位均无政府性基金和国有资本经营预算拨款。")
        lines.append("")

    # 解析失败的文件
    if error_records:
        lines.append("## 四、解析失败的文件")
        lines.append("")
        for r in error_records:
            lines.append(f"- `{r.get('file', '-')}` ({r.get('year', '-')}, {r.get('unit', '-')}): {r.get('error', r.get('status', ''))}")
        lines.append("")

    report_text = "\n".join(lines)

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report_text)

    logger.info("报告已生成: %s", REPORT_FILE)
    return str(REPORT_FILE)


# ============================================================================
# 入口
# ============================================================================


def main():
    logger.info("=" * 60)
    logger.info("徐汇区教育局预算财政拨款分析")
    logger.info("PDF目录: %s", PDF_DIR)
    logger.info("最小有效文件: %d KB", MIN_PDF_SIZE // 1000)
    logger.info("=" * 60)

    # 分析所有PDF
    results = analyze_all_pdfs()

    # 保存数据
    save_data(results)

    # 生成报告
    report_path = generate_report(results)

    # 输出摘要
    ok_count = sum(1 for r in results if r.get("status") == "ok")
    print(f"\n分析完成！")
    print(f"  成功提取: {ok_count} 个文件")
    print(f"  数据文件: {BUDGET_DATA_FILE}")
    print(f"  分析报告: {report_path}")


if __name__ == "__main__":
    main()
