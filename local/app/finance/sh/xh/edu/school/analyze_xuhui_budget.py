#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
徐汇区各部门2026年预算PDF - 统计分析脚本

功能:
1. 遍历所有已下载的预算PDF（src下所有目录）
2. 提取：财政拨款收入、一般公共预算、政府性基金、国有资本经营预算
3. 按层级分类统计（区级部门/街镇/教育系统/卫生健康系统）
4. 输出CSV文件（分层级 + 汇总）

数据提取策略:
- 优先从预算编制说明文本提取（万元）
- 后备从财务收支预算总表提取（元→万元）
"""

import os, re, sys, json, csv, logging
from pathlib import Path
from collections import defaultdict
from datetime import datetime

if sys.platform == 'win32':
    try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except: pass

import pdfplumber

# ========== 配置 ==========
SCRIPT_DIR = Path(__file__).parent
SRC_DIR = SCRIPT_DIR / "src"
OUTPUT_CSV = SRC_DIR / "xuhui_budget_2026_stats.csv"
SUMMARY_CSV = SRC_DIR / "xuhui_budget_2026_summary.csv"
LOG_FILE = SRC_DIR / "logs" / "analyze_xuhui.log"

MIN_PDF_SIZE = 5000  # 小于5KB视为无效

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_FILE, encoding='utf-8')],
)
logger = logging.getLogger(__name__)

# ========== 层级分类 ==========

# 党委部门
DANGWEI = [
    '区纪律检查委员会', '监察委员会', '区委办公室', '区委组织部', '区委宣传部', '区委统战部',
    '区委社工部', '区委政法委', '区区级机关工作党委', '区委老干部局', '区档案局', '区委党校',
]

# 政府部门
ZHENGFU = [
    '区政府办公室', '区发展和改革委员会', '区新型工业化推进办', '区商务委员会',
    '区教育局', '区科学技术委员会', '公安分局', '区民政局', '区司法局', '区财政局',
    '区人力资源和社会保障局', '区规划和自然资源局', '区生态环境局',
    '区建设和管理委员会', '区文化和旅游局', '区卫生健康委员会', '区退役军人事务局',
    '区应急管理局', '区审计局', '区市场监督管理局', '区国有资产监督管理委员会',
    '区体育局', '区统计局', '区医疗保障局', '区绿化和市容管理局',
    '区住房保障和房屋管理局', '区城市管理行政执法局', '区国动办', '区数据局',
    '区城市运行管理中心', '区投促办', '区营商服务中心', '区机关事务管理局',
    '南站管委办', '信访办公室', '金融办', '地区工作办公室',
]

# 人大政协
RENDA_ZHENGXIE = ['区人大常委办公室', '区政协办公室']

# 人民团体
TUANTI = ['区总工会', '团区委', '区妇联', '区工商联', '区科协', '区残联', '区红十字会']

# 街道/镇
JIEDAO = [
    '徐家汇街道', '天平街道', '湖南街道', '枫林街道', '斜土街道',
    '田林街道', '长桥街道', '虹梅街道', '康健街道', '龙华街道',
    '凌云街道', '漕河泾街道', '华泾镇',
]


def classify_level(dir_name):
    """根据目录/文件名判断层级"""
    for kw in DANGWEI:
        if kw in dir_name:
            return '党委部门'
    for kw in JIEDAO:
        if kw in dir_name:
            return '街镇'
    for kw in RENDA_ZHENGXIE:
        if kw in dir_name:
            return '人大政协'
    for kw in TUANTI:
        if kw in dir_name:
            return '人民团体'
    for kw in ZHENGFU:
        if kw in dir_name:
            return '政府部门'
    if '教育系统' in dir_name:
        return '教育系统'
    if '卫生健康系统' in dir_name:
        return '卫生健康系统'
    # 对于pdf/目录下的学校文件，从文件名判断
    return '未知'


def is_education_unit(filename):
    """判断是否为教育系统下属单位（学校等）- 用于pdf/目录中扁平文件"""
    edu_keywords = ['中学', '小学', '幼儿园', '学校', '职校', '教育', '位育', '南洋',
                    '向阳', '乌鲁木齐', '信息管理', '业余', '社区学院', '教师进修']
    return any(kw in filename for kw in edu_keywords)


def is_health_unit(filename):
    """判断是否为卫生健康系统单位"""
    health_keywords = ['医院', '卫生', '疾控', '健康', '医疗', '社区卫生', '妇幼']
    return any(kw in filename for kw in health_keywords)


# ========== PDF 解析 ==========

def find_budget_text_page(pdf):
    """查找包含财政拨款收入数据的页码（跳过名词解释页）"""
    for i, page in enumerate(pdf.pages):
        text = page.extract_text()
        if not text:
            continue
        # 必须同时有"收入预算"（数据页标志）和财政拨款收入+数字
        if '收入预算' in text and re.search(r"(?<!非同级)财政拨款收入?\s*[\d,]+\.?\d*", text):
            return i
    return None


def extract_from_text(page_text):
    """从预算编制说明文本中提取财政拨款数据（万元）"""
    text = page_text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    result = {}

    # 1. 财政拨款收入
    m = re.search(r"(?<!非同级)财政拨款收入?\s*([\d,]+\.?\d*)\s*万\s*元", text)
    if not m:
        return None
    result["财政拨款收入"] = float(m.group(1).replace(",", ""))

    # 2. 找到三项明细锚点
    three_items = {}
    for anchor in ["财政拨款支出预算中", "。其中，"]:
        idx = text.find(anchor)
        if idx >= 0:
            section = text[idx + len(anchor):]
            numbers = re.findall(r"拨\s*款\s*支\s*出\s*预\s*算\s*([\d,]+\.?\d*)\s*万\s*元", section)
            if numbers:
                three_items["一般公共预算"] = float(numbers[0].replace(",", ""))
                if len(numbers) > 1:
                    three_items["政府性基金"] = float(numbers[1].replace(",", ""))
                if len(numbers) > 2:
                    three_items["国有资本经营预算"] = float(numbers[2].replace(",", ""))
            break

    result["一般公共预算"] = three_items.get("一般公共预算")
    result["政府性基金"] = three_items.get("政府性基金")
    result["国有资本经营预算"] = three_items.get("国有资本经营预算")

    # 3. 后备正则
    fallback = {
        "一般公共预算": r"一般\s*公共\s*预\s*算\s*拨\s*款\s*支\s*出\s*预\s*算\s*([\d,]+\.?\d*)\s*万\s*元",
        "政府性基金": r"政府性\s*基金\s*拨\s*款\s*支\s*出\s*预\s*算\s*([\d,]+\.?\d*)\s*万\s*元",
        "国有资本经营预算": r"国有\s*资本\s*经营\s*预\s*算\s*拨\s*款\s*支\s*出\s*预\s*算\s*([\d,]+\.?\d*)\s*万\s*元",
    }
    for key, pat in fallback.items():
        if result.get(key) is None:
            m = re.search(pat, text)
            if m:
                result[key] = float(m.group(1).replace(",", ""))

    # 4. 推断：如果其他两项都是0，一般公共预算=财政拨款收入
    if result.get("一般公共预算") is None:
        gf = result.get("政府性基金")
        gc = result.get("国有资本经营预算")
        if (gf is not None and gf == 0) and (gc is not None and gc == 0):
            result["一般公共预算"] = result["财政拨款收入"]

    for key in ["一般公共预算", "政府性基金", "国有资本经营预算"]:
        if key not in result:
            result[key] = None

    return result


def extract_from_table(pdf):
    """从财务收支预算总表中提取数据（元→万元）"""
    for page in pdf.pages:
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
                first_cell = str(row[0]).strip() if row[0] else ""
                value_str = str(row[1]).replace(",", "").strip() if len(row) > 1 and row[1] else ""

                if "一、" in first_cell and "财政拨款收入" in first_cell:
                    try: result["财政拨款收入"] = float(value_str) / 10000 if value_str else 0
                    except: pass
                elif "1、一般公共预算" in first_cell or ("1、" in first_cell and "般公共" in first_cell):
                    try: result["一般公共预算"] = float(value_str) / 10000 if value_str else 0
                    except: pass
                elif "2、政府性基金" in first_cell:
                    try: result["政府性基金"] = float(value_str) / 10000 if value_str else 0
                    except: pass
                elif "3、国有资本经营预算" in first_cell:
                    try: result["国有资本经营预算"] = float(value_str) / 10000 if value_str else 0
                    except: pass

        if result.get("财政拨款收入") is not None:
            for key in ["一般公共预算", "政府性基金", "国有资本经营预算"]:
                if key not in result or result[key] is None:
                    result[key] = 0.0
            return result

    return None


def parse_pdf_filename(filepath):
    """从文件路径解析年份、单位名称、层级"""
    name = Path(filepath).stem

    # 年份
    year_match = re.search(r"(\d{4})年度", name)
    year = year_match.group(1) if year_match else None

    # 单位名称
    unit = name
    # 去掉年度后缀
    unit = re.sub(r'\d{4}年度.*', '', unit).strip()
    # 去掉编号前缀
    unit = re.sub(r'^\d+\s*', '', unit).strip()

    return year, unit, name


# ========== 遍历所有PDF ==========

def find_all_pdfs():
    """扫描src目录下所有2026年预算PDF"""
    pdfs = []
    for root, dirs, files in os.walk(SRC_DIR):
        for f in files:
            if not f.lower().endswith('.pdf'):
                continue
            filepath = Path(root) / f
            if filepath.stat().st_size < MIN_PDF_SIZE:
                continue
            if '2026' not in f and '2026' not in str(root):
                continue

            # 确定所属部门/目录名称
            rel_path = filepath.relative_to(SRC_DIR)
            parts = rel_path.parts
            # parts[0] 是顶层目录(budget_pdfs_2026/xuhui_budget_2026/pdf)
            # parts[1] 是部门子目录名（如果有的话）
            if len(parts) >= 3:
                dir_name = parts[1]  # 子目录名（部门名）
            elif len(parts) == 2 and parts[0] in ('pdf',):
                dir_name = parts[0]  # pdf目录扁平结构
            else:
                dir_name = parts[0]  # 根目录下的文件

            pdfs.append({
                'path': filepath,
                'filename': f,
                'dir': dir_name,
                'rel_path': str(rel_path),
            })
    return pdfs


# ========== 主分析流程 ==========

def analyze_all():
    """分析所有PDF并返回记录列表"""
    pdfs = find_all_pdfs()
    logger.info(f"找到 {len(pdfs)} 个2026年预算PDF")

    records = []
    ok_count = 0
    fail_count = 0

    for i, pdf_info in enumerate(pdfs):
        filepath = pdf_info['path']
        year, unit, fullname = parse_pdf_filename(filepath)

        # 判断层级
        dir_name = pdf_info['dir']
        level = classify_level(dir_name)
        if level == '未知' and dir_name == '':
            # pdf/目录中的扁平文件
            if is_education_unit(fullname):
                level = '教育系统'
            elif is_health_unit(fullname):
                level = '卫生健康系统'
            else:
                level = classify_level(fullname)

        if (i + 1) % 50 == 0:
            logger.info(f"进度: {i+1}/{len(pdfs)}")

        try:
            with pdfplumber.open(filepath) as pdf:
                text_page_idx = find_budget_text_page(pdf)
                data = None
                source = "text"

                if text_page_idx is not None:
                    page_text = pdf.pages[text_page_idx].extract_text()
                    data = extract_from_text(page_text)

                if data is None:
                    data = extract_from_table(pdf)
                    source = "table" if data else "unknown"

                if data is None:
                    fail_count += 1
                    continue

                ok_count += 1
                record = {
                    '层级': level,
                    '目录': pdf_info['dir'],
                    '文件名': pdf_info['filename'],
                    '年份': year,
                    '单位名称': unit,
                    '财政拨款收入(万元)': round(data.get('财政拨款收入', 0) or 0, 2),
                    '一般公共预算(万元)': round(data.get('一般公共预算', 0) or 0, 2),
                    '政府性基金(万元)': round(data.get('政府性基金', 0) or 0, 2),
                    '国有资本经营预算(万元)': round(data.get('国有资本经营预算', 0) or 0, 2),
                    '数据来源': source,
                }
                records.append(record)

        except Exception as e:
            fail_count += 1

    logger.info(f"分析完成: 成功{ok_count}, 失败{fail_count}")
    return records


def generate_csv(records):
    """生成CSV统计报告"""
    if not records:
        logger.error("无有效数据，无法生成CSV")
        return

    # ===== 1. 明细CSV =====
    fieldnames = ['层级', '目录', '单位名称', '文件名', '年份',
                  '财政拨款收入(万元)', '一般公共预算(万元)',
                  '政府性基金(万元)', '国有资本经营预算(万元)', '数据来源']

    with open(OUTPUT_CSV, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for r in sorted(records, key=lambda x: (x['层级'], x['目录'], x['单位名称'])):
            writer.writerow(r)

    logger.info(f"明细CSV已保存: {OUTPUT_CSV} ({len(records)}行)")

    # ===== 2. 汇总CSV（按层级+目录） =====
    # 按层级汇总
    level_summary = defaultdict(lambda: {
        '单位数': set(), '财政拨款收入': 0.0, '一般公共预算': 0.0,
        '政府性基金': 0.0, '国有资本经营预算': 0.0,
    })

    # 按层级+目录汇总
    detail_summary = defaultdict(lambda: {
        '单位数': set(), '财政拨款收入': 0.0, '一般公共预算': 0.0,
        '政府性基金': 0.0, '国有资本经营预算': 0.0,
    })

    for r in records:
        level = r['层级']
        dir_name = r['目录']
        unit_name = r['单位名称']

        for summary_dict, key in [(level_summary, level), (detail_summary, (level, dir_name))]:
            s = summary_dict[key]
            s['单位数'].add(unit_name)
            s['财政拨款收入'] += r['财政拨款收入(万元)']
            s['一般公共预算'] += r['一般公共预算(万元)']
            s['政府性基金'] += r['政府性基金(万元)']
            s['国有资本经营预算'] += r['国有资本经营预算(万元)']

    with open(SUMMARY_CSV, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)

        # 表头
        writer.writerow(['徐汇区2026年度部门预算统计汇总'])
        writer.writerow([f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
        writer.writerow([f'总记录数: {len(records)}'])
        writer.writerow([])

        # 分目录明细
        writer.writerow(['层级', '目录', '单位数', '财政拨款收入(万元)',
                         '一般公共预算(万元)', '政府性基金(万元)', '国有资本经营预算(万元)'])
        for (level, dir_name), s in sorted(detail_summary.items(),
                                            key=lambda x: (x[0][0], x[0][1])):
            writer.writerow([
                level, dir_name, len(s['单位数']),
                round(s['财政拨款收入'], 2),
                round(s['一般公共预算'], 2),
                round(s['政府性基金'], 2),
                round(s['国有资本经营预算'], 2),
            ])

        writer.writerow([])

        # 按层级汇总
        writer.writerow(['层级汇总'])
        writer.writerow(['层级', '单位数', '财政拨款收入(万元)',
                         '一般公共预算(万元)', '政府性基金(万元)', '国有资本经营预算(万元)'])

        grand_total = {'units': 0, 'sr': 0, 'gg': 0, 'gf': 0, 'gc': 0}
        level_order = ['党委部门', '政府部门', '人大政协', '人民团体', '街镇', '教育系统', '卫生健康系统']
        for level in level_order:
            if level not in level_summary:
                continue
            s = level_summary[level]
            writer.writerow([
                level, len(s['单位数']),
                round(s['财政拨款收入'], 2),
                round(s['一般公共预算'], 2),
                round(s['政府性基金'], 2),
                round(s['国有资本经营预算'], 2),
            ])
            grand_total['units'] += len(s['单位数'])
            grand_total['sr'] += s['财政拨款收入']
            grand_total['gg'] += s['一般公共预算']
            grand_total['gf'] += s['政府性基金']
            grand_total['gc'] += s['国有资本经营预算']

        writer.writerow([])
        writer.writerow(['合计', grand_total['units'],
                         round(grand_total['sr'], 2),
                         round(grand_total['gg'], 2),
                         round(grand_total['gf'], 2),
                         round(grand_total['gc'], 2)])

    logger.info(f"汇总CSV已保存: {SUMMARY_CSV}")
    logger.info(f"\n=== 快览 ===")
    logger.info(f"  党委部门: {level_summary.get('党委部门', {}).get('财政拨款收入', 0):,.2f}万")
    logger.info(f"  政府部门: {level_summary.get('政府部门', {}).get('财政拨款收入', 0):,.2f}万")
    logger.info(f"  街镇:     {level_summary.get('街镇', {}).get('财政拨款收入', 0):,.2f}万")
    logger.info(f"  教育系统: {level_summary.get('教育系统', {}).get('财政拨款收入', 0):,.2f}万")
    logger.info(f"  合计:     {grand_total['sr']:,.2f}万元")


def main():
    logger.info("=" * 60)
    logger.info("徐汇区2026年预算PDF统计分析")
    logger.info("=" * 60)

    records = analyze_all()
    if records:
        generate_csv(records)
        print(f"\n完成！")
        print(f"  明细: {OUTPUT_CSV}")
        print(f"  汇总: {SUMMARY_CSV}")
    else:
        print("无有效数据！")


if __name__ == '__main__':
    main()
