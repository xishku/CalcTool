#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仅分析 budget_pdfs_2026 目录下的 2026 年预算 PDF
按层级分项统计，输出 CSV
"""

import os, re, sys, csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime

if sys.platform == 'win32':
    try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except: pass

import pdfplumber

# ========== 配置 ==========
SCRIPT_DIR = Path(__file__).parent
SRC_DIR = SCRIPT_DIR / "src" / "budget_pdfs_2026"  # 仅此目录
OUTPUT_CSV = SCRIPT_DIR / "src" / "budget_pdfs_2026_stats.csv"
SUMMARY_CSV = SCRIPT_DIR / "src" / "budget_pdfs_2026_summary.csv"
MIN_PDF_SIZE = 5000

print(f"分析目录: {SRC_DIR}")
print(f"输出CSV:  {OUTPUT_CSV}")
print(f"汇总CSV:  {SUMMARY_CSV}")
print()

# ========== 层级分类关键词 ==========
LEVEL_RULES = [
    # (层级名, 匹配关键词列表)
    ('党委部门', [
        '区纪律检查委员会', '监察委员会', '区委办公室', '区委组织部', '区委宣传部',
        '区委统战部', '区委社工部', '区委政法委', '区区级机关工作党委', '区委老干部局',
        '区档案局', '区委党校',
    ]),
    ('政府部门', [
        '区政府办公室', '区发展和改革委员会', '区新型工业化推进办', '区商务委员会',
        '区教育局', '区科学技术委员会', '公安分局', '区民政局', '区司法局', '区财政局',
        '区人力资源和社会保障局', '区规划和自然资源局', '区生态环境局',
        '区建设和管理委员会', '区文化和旅游局', '区卫生健康委员会', '区退役军人事务局',
        '区应急管理局', '区审计局', '区市场监督管理局', '区国有资产监督管理委员会',
        '区体育局', '区统计局', '区医疗保障局', '区绿化和市容管理局',
        '区住房保障和房屋管理局', '区城市管理行政执法局', '区国动办', '区数据局',
        '区城市运行管理中心', '区投促办', '区营商服务中心', '区机关事务管理局',
        '南站管委办', '信访办公室', '金融办', '地区工作办公室',
    ]),
    ('人大政协', ['区人大常委办公室', '区政协办公室']),
    ('人民团体', ['区总工会', '团区委', '区妇联', '区工商联', '区科协', '区残联', '区红十字会']),
    ('街镇', [
        '徐家汇街道', '天平街道', '湖南街道', '枫林街道', '斜土街道',
        '田林街道', '长桥街道', '虹梅街道', '康健街道', '龙华街道',
        '凌云街道', '漕河泾街道', '华泾镇',
    ]),
    ('教育系统', ['教育系统']),
    ('卫生健康系统', ['卫生健康系统']),
]


def classify(dir_name, filename):
    """根据目录名和文件名判断层级"""
    combined = dir_name + filename
    for level_name, keywords in LEVEL_RULES:
        for kw in keywords:
            if kw in combined:
                return level_name
    # 后备：从文件名判断教育/卫生
    for kw in ['中学', '小学', '幼儿园', '学校', '职校', '教育', '位育', '南洋',
               '向阳', '乌鲁木齐', '信息管理', '业余', '社区学院', '教师进修', '学前']:
        if kw in filename:
            return '教育系统'
    for kw in ['医院', '卫生', '疾控', '健康', '医疗', '社区卫生', '妇幼']:
        if kw in filename:
            return '卫生健康系统'
    return '未知'


# ========== PDF 解析 ==========

def find_budget_text_page(pdf):
    for i, page in enumerate(pdf.pages):
        text = page.extract_text()
        if not text:
            continue
        if '收入预算' in text and re.search(r"(?<!非同级)财政拨款收入?\s*[\d,]+\.?\d*", text):
            return i
    return None


def extract_from_text(page_text):
    text = page_text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    # 财政拨款收入
    m = re.search(r"(?<!非同级)财政拨款收入?\s*([\d,]+\.?\d*)\s*万\s*元", text)
    if not m:
        return None

    result = {"财政拨款收入": float(m.group(1).replace(",", ""))}

    # 三项明细
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

    # 后备正则
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

    # 如果其他两项都是0，一般公共预算=财政拨款收入
    if result.get("一般公共预算") is None:
        gf = result.get("政府性基金")
        gc = result.get("国有资本经营预算")
        if (gf is not None and gf == 0) and (gc is not None and gc == 0):
            result["一般公共预算"] = result["财政拨款收入"]

    for key in ["一般公共预算", "政府性基金", "国有资本经营预算"]:
        result.setdefault(key, None)

    return result


def extract_from_table(pdf):
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
                result.setdefault(key, 0.0)
            return result
    return None


# ========== 主流程 ==========

def main():
    # 扫描所有 PDF
    pdfs = []
    for root, dirs, files in os.walk(SRC_DIR):
        for f in files:
            if not f.lower().endswith('.pdf'):
                continue
            fp = Path(root) / f
            if fp.stat().st_size < MIN_PDF_SIZE:
                continue
            rel = fp.relative_to(SRC_DIR)
            parts = rel.parts
            dir_name = parts[0] if len(parts) > 1 else '(根目录)'
            pdfs.append({'path': fp, 'filename': f, 'dir': dir_name})

    print(f"找到 {len(pdfs)} 个 PDF 文件")

    # 按目录统计
    dir_counts = defaultdict(int)
    for p in pdfs:
        dir_counts[p['dir']] += 1
    print(f"共 {len(dir_counts)} 个部门/系统目录\n")

    # 逐个解析
    records = []
    ok, fail = 0, 0

    for i, p in enumerate(pdfs):
        fp = p['path']
        fname = p['filename']
        dir_name = p['dir']

        # 年份
        ym = re.search(r"(\d{4})年度", fname)
        year = ym.group(1) if ym else '2026'

        # 单位名称
        unit = re.sub(r'\d{4}年度.*', '', re.sub(r'^\d+\s*', '', Path(fp).stem)).strip()

        # 层级
        level = classify(dir_name, fname)

        if (i + 1) % 50 == 0:
            print(f"  进度: {i+1}/{len(pdfs)} (成功{ok}, 失败{fail})")

        try:
            with pdfplumber.open(fp) as pdf:
                tpi = find_budget_text_page(pdf)
                data = None
                source = "text"
                if tpi is not None:
                    data = extract_from_text(pdf.pages[tpi].extract_text())
                if data is None:
                    data = extract_from_table(pdf)
                    source = "table" if data else "unknown"
                if data is None:
                    fail += 1
                    continue
                ok += 1
                records.append({
                    '层级': level,
                    '目录': dir_name,
                    '单位名称': unit,
                    '文件名': fname,
                    '年份': year,
                    '财政拨款收入(万元)': round(data.get('财政拨款收入', 0) or 0, 2),
                    '一般公共预算(万元)': round(data.get('一般公共预算', 0) or 0, 2),
                    '政府性基金(万元)': round(data.get('政府性基金', 0) or 0, 2),
                    '国有资本经营预算(万元)': round(data.get('国有资本经营预算', 0) or 0, 2),
                    '数据来源': source,
                })
        except Exception as e:
            fail += 1

    print(f"\n解析完成: 成功 {ok}, 失败 {fail}")

    if not records:
        print("无有效数据！")
        return

    # ===== 输出明细 CSV =====
    fields = ['层级', '目录', '单位名称', '文件名', '年份',
              '财政拨款收入(万元)', '一般公共预算(万元)',
              '政府性基金(万元)', '国有资本经营预算(万元)', '数据来源']

    with open(OUTPUT_CSV, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for r in sorted(records, key=lambda x: (x['层级'], x['目录'], x['单位名称'])):
            w.writerow(r)
    print(f"明细: {OUTPUT_CSV} ({len(records)} 行)")

    # ===== 汇总 CSV =====
    level_agg = defaultdict(lambda: dict(units=set(), sr=0.0, gg=0.0, gf=0.0, gc=0.0))
    detail_agg = defaultdict(lambda: dict(units=set(), sr=0.0, gg=0.0, gf=0.0, gc=0.0))

    for r in records:
        for agg, key in [(level_agg, r['层级']), (detail_agg, (r['层级'], r['目录']))]:
            s = agg[key]
            s['units'].add(r['单位名称'])
            s['sr'] += r['财政拨款收入(万元)']
            s['gg'] += r['一般公共预算(万元)']
            s['gf'] += r['政府性基金(万元)']
            s['gc'] += r['国有资本经营预算(万元)']

    with open(SUMMARY_CSV, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['徐汇区2026年度部门预算统计汇总 (仅budget_pdfs_2026)'])
        w.writerow([f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
        w.writerow([f'总记录数: {len(records)}'])
        w.writerow([])

        # 分目录明细
        w.writerow(['层级', '目录', '单位数', '财政拨款收入(万元)',
                     '一般公共预算(万元)', '政府性基金(万元)', '国有资本经营预算(万元)'])
        for (level, dn), s in sorted(detail_agg.items(), key=lambda x: (x[0][0], x[0][1])):
            w.writerow([level, dn, len(s['units']),
                        round(s['sr'], 2), round(s['gg'], 2), round(s['gf'], 2), round(s['gc'], 2)])

        w.writerow([])
        w.writerow(['层级汇总（按大类统计，可以折叠查看）'])
        w.writerow(['层级', '单位数(去重)', '财政拨款收入(万元)',
                     '一般公共预算(万元)', '政府性基金(万元)', '国有资本经营预算(万元)'])

        grand = dict(units=0, sr=0, gg=0, gf=0, gc=0)
        order = ['党委部门', '政府部门', '人大政协', '人民团体', '街镇', '教育系统', '卫生健康系统']
        for level in order:
            if level not in level_agg:
                continue
            s = level_agg[level]
            w.writerow([level, len(s['units']), round(s['sr'], 2),
                        round(s['gg'], 2), round(s['gf'], 2), round(s['gc'], 2)])
            grand['units'] += len(s['units'])
            grand['sr'] += s['sr']
            grand['gg'] += s['gg']
            grand['gf'] += s['gf']
            grand['gc'] += s['gc']

        # 还有未知的也加上
        if '未知' in level_agg:
            s = level_agg['未知']
            w.writerow(['未知', len(s['units']), round(s['sr'], 2),
                        round(s['gg'], 2), round(s['gf'], 2), round(s['gc'], 2)])
            grand['units'] += len(s['units'])
            grand['sr'] += s['sr']
            grand['gg'] += s['gg']
            grand['gf'] += s['gf']
            grand['gc'] += s['gc']

        w.writerow([])
        w.writerow(['合计', grand['units'], round(grand['sr'], 2),
                     round(grand['gg'], 2), round(grand['gf'], 2), round(grand['gc'], 2)])

    print(f"汇总: {SUMMARY_CSV}")

    # ===== 终端快览 =====
    print("\n" + "=" * 70)
    print("徐汇区 2026 年预算统计快览 (仅 budget_pdfs_2026)")
    print("=" * 70)
    print(f"{'层级':12s} | {'单位数':>5s} | {'财政拨款收入(万元)':>18s} | {'一般公共预算':>14s} | {'政府性基金':>12s} | {'国资本':>10s}")
    print("-" * 70)
    for level in order:
        if level not in level_agg:
            continue
        s = level_agg[level]
        print(f"{level:12s} | {len(s['units']):5d} | {s['sr']:18,.2f} | {s['gg']:14,.2f} | {s['gf']:12,.2f} | {s['gc']:10,.2f}")
    if '未知' in level_agg:
        s = level_agg['未知']
        print(f"{'未知':12s} | {len(s['units']):5d} | {s['sr']:18,.2f} | {s['gg']:14,.2f} | {s['gf']:12,.2f} | {s['gc']:10,.2f}")
    print("-" * 70)
    print(f"{'合计':12s} | {grand['units']:5d} | {grand['sr']:18,.2f} | {grand['gg']:14,.2f} | {grand['gf']:12,.2f} | {grand['gc']:10,.2f}")
    print(f"\n明细CSV: {OUTPUT_CSV}")
    print(f"汇总CSV: {SUMMARY_CSV}")


if __name__ == '__main__':
    main()
