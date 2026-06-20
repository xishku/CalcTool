#!/usr/bin/env python3
"""
budget_pdfs_2026 目录统计分析 + 与总预算对比
输出: budget_pdfs_2026_comparison.csv (含对比)
"""

import csv, os, re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
SRC_DIR = SCRIPT_DIR / "src" / "budget_pdfs_2026"
STATS_CSV = SCRIPT_DIR / "src" / "budget_pdfs_2026_stats.csv"
OUT_CSV = SCRIPT_DIR / "src" / "budget_pdfs_2026_comparison.csv"

# ===== 读取已有分析结果 =====
if not os.path.exists(STATS_CSV):
    print("请先运行 analyze_budget_pdfs_2026.py 生成明细CSV")
    exit(1)

records = []
with open(STATS_CSV, 'r', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        records.append(r)
print(f"读取 {len(records)} 条记录")

# ===== 按目录+层级汇总 =====
dir_agg = defaultdict(lambda: dict(units=set(), count=0, sr=0.0, gg=0.0, gf=0.0, gc=0.0))
level_agg = defaultdict(lambda: dict(units=set(), count=0, sr=0.0, gg=0.0, gf=0.0, gc=0.0))

for r in records:
    level = r['层级']
    dn = r['目录']
    un = r['单位名称']
    sr = float(r['财政拨款收入(万元)'])
    gg = float(r['一般公共预算(万元)'])
    gf = float(r['政府性基金(万元)'])
    gc = float(r['国有资本经营预算(万元)'])

    for agg, key in [(dir_agg, (level, dn)), (level_agg, level)]:
        s = agg[key]
        s['units'].add(un)
        s['count'] += 1
        s['sr'] += sr
        s['gg'] += gg
        s['gf'] += gf
        s['gc'] += gc

# ===== 总预算PDF关键数据（手动提取） =====
master = {
    '一般公共预算收入预算': 3154500,      # 315.45亿元 -> 万元 (收入)
    '一般公共预算支出预算': 4032900,      # 403.29亿元 -> 万元
    '其中区本级支出': 3796200,            # 379.62亿元
    '其中镇级支出': 80000,               # 8.00亿元
    '政府性基金收入预算': 1503066,       # 150.31亿元 (从P122表格)
    '政府性基金支出预算合计': 1628009,    # 估算: 城乡社区1,621,392 + 文旅46 + 住房420 + 其他6,151
    '国有资本经营收入合计': 25155,       # 2.52亿元 (从P130表格)
    '国有资本经营支出合计': 22645,       # 2.27亿元
    '收入总量(一般公共预算)': 4174700,
    '支出总量(一般公共预算)': 4174700,
}

master_notes = [
    '一般公共预算收入315.45亿+上级补助42.00亿+调入0.92亿+稳定调节基金54.92亿+上年结转4.18亿=收入总量417.47亿',
    '一般公共预算支出403.29亿(区本级379.62+镇级8.00+上级专项15.67)+上解11.00亿+债务还本3.18亿=支出总量417.47亿',
    '政府性基金支出: 城乡社区1,621,392万+文旅46万+住房420万+其他6,151万≈162.80亿(不含债务还本及转移支付)',
    '国有资本经营支出2.27亿(含解决历史遗留问题0.11亿+国企资本金注入2.16亿)+调出0.92亿+结转0.15亿',
]

# ===== 部门分析总计 =====
total_sr = sum(s['sr'] for s in dir_agg.values())
total_gg = sum(s['gg'] for s in dir_agg.values())
total_gf = sum(s['gf'] for s in dir_agg.values())
total_gc = sum(s['gc'] for s in dir_agg.values())
total_units = len(set().union(*(s['units'] for s in dir_agg.values())))

print(f"部门分析总计: {total_units}单位, 财政拨款{total_sr:,.2f}万={total_sr/10000:.2f}亿")
print(f"  一般公共预算: {total_gg:,.2f}万={total_gg/10000:.2f}亿")
print(f"  政府性基金:   {total_gf:,.2f}万={total_gf/10000:.2f}亿")
print(f"  国有资本:     {total_gc:,.2f}万")

# ===== 输出对比 CSV =====
with open(OUT_CSV, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)

    # 标题
    w.writerow(['徐汇区2026年度部门预算统计分析 (budget_pdfs_2026目录)'])
    w.writerow([f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
    w.writerow([f'PDF来源: {len(records)}条记录, 去重{total_units}个预算单位'])
    w.writerow([])

    # === Part A: 分目录明细 ===
    w.writerow(['【一、分目录/分项明细】'])
    w.writerow(['层级', '目录(部门/系统)', 'PDF数', '单位数(去重)', '财政拨款收入(万元)',
                '一般公共预算(万元)', '政府性基金(万元)', '国有资本经营预算(万元)'])

    level_order = ['党委部门', '政府部门', '人大政协', '人民团体', '街镇', '教育系统', '卫生健康系统']
    for lv in level_order:
        dirs_in_level = [(dn, s) for (level, dn), s in dir_agg.items() if level == lv]
        if not dirs_in_level:
            continue
        # 层级小计行
        ls = level_agg[lv]
        w.writerow([f'▶ {lv} (小计)', '', ls['count'], len(ls['units']),
                    round(ls['sr'], 2), round(ls['gg'], 2), round(ls['gf'], 2), round(ls['gc'], 2)])
        for dn, s in sorted(dirs_in_level, key=lambda x: -x[1]['sr']):
            w.writerow(['', dn, s['count'], len(s['units']),
                        round(s['sr'], 2), round(s['gg'], 2), round(s['gf'], 2), round(s['gc'], 2)])

    # 未知
    unknown = [(dn, s) for (level, dn), s in dir_agg.items() if level == '未知']
    if unknown:
        w.writerow(['▶ 未知 (小计)', '', sum(x[1]['count'] for x in unknown),
                    sum(len(x[1]['units']) for x in unknown),
                    round(sum(x[1]['sr'] for x in unknown), 2),
                    round(sum(x[1]['gg'] for x in unknown), 2),
                    round(sum(x[1]['gf'] for x in unknown), 2),
                    round(sum(x[1]['gc'] for x in unknown), 2)])

    w.writerow([])

    # === Part B: 层级汇总 ===
    w.writerow(['【二、按层级大类汇总】'])
    w.writerow(['层级', 'PDF数', '单位数(去重)', '财政拨款收入(万元)',
                '一般公共预算(万元)', '政府性基金(万元)', '国有资本经营预算(万元)'])

    grand = dict(cnt=0, units=0, sr=0, gg=0, gf=0, gc=0)
    for lv in level_order:
        if lv not in level_agg:
            continue
        s = level_agg[lv]
        w.writerow([lv, s['count'], len(s['units']), round(s['sr'], 2),
                    round(s['gg'], 2), round(s['gf'], 2), round(s['gc'], 2)])
        grand['cnt'] += s['count']
        grand['units'] += len(s['units'])
        grand['sr'] += s['sr']
        grand['gg'] += s['gg']
        grand['gf'] += s['gf']
        grand['gc'] += s['gc']
    if '未知' in level_agg:
        s = level_agg['未知']
        w.writerow(['未知', s['count'], len(s['units']), round(s['sr'], 2),
                    round(s['gg'], 2), round(s['gf'], 2), round(s['gc'], 2)])
        grand['cnt'] += s['count']
        grand['units'] += len(s['units'])
        grand['sr'] += s['sr']
        grand['gg'] += s['gg']
        grand['gf'] += s['gf']
        grand['gc'] += s['gc']

    w.writerow(['部门分析合计', grand['cnt'], grand['units'],
                round(grand['sr'], 2), round(grand['gg'], 2),
                round(grand['gf'], 2), round(grand['gc'], 2)])
    w.writerow([])

    # === Part C: 与总预算对比 ===
    w.writerow(['【三、与总预算草案对比】'])
    w.writerow(['(数据来源: 上海市徐汇区2025年预算执行情况和2026年预算草案的附表及说明.pdf)'])
    w.writerow([])

    w.writerow(['对比项目', '部门分析合计(万元)', '总预算草案(万元)', '差异(万元)', '说明'])
    w.writerow(['一般公共预算支出', round(grand['gg'], 2), master['一般公共预算支出预算'],
                round(grand['gg'] - master['一般公共预算支出预算'], 2),
                '总预算含区本级379.62亿+镇级8.00亿+上级专项15.67亿；部门分析含教育局等委办局分配的预算，但教育系统/卫生系统与主管局可能重叠'])
    w.writerow(['政府性基金支出', round(grand['gf'], 2), master['政府性基金支出预算合计'],
                round(grand['gf'] - master['政府性基金支出预算合计'], 2),
                '总预算162.80亿含土地出让、基建等；部门分析中建管委等占较大比重'])
    w.writerow(['国有资本经营预算支出', round(grand['gc'], 2), master['国有资本经营支出合计'],
                round(grand['gc'] - master['国有资本经营支出合计'], 2),
                f'总预算{master["国有资本经营支出合计"]}万(2.27亿)；部门预算中该科目数额较小'])
    w.writerow([])

    # 总预算草案原文关键数据
    w.writerow(['【四、总预算草案原文关键数据】'])
    w.writerow(['项目', '数值(万元)', '数值(亿元)', '来源/说明'])
    w.writerow(['一般公共预算收入', 3154500, 315.45, '2026年区本级一般公共预算收入预算'])
    w.writerow(['上级补助收入', 420000, 42.00, ''])
    w.writerow(['调入资金', 9200, 0.92, '从国有资本经营预算调入'])
    w.writerow(['动用预算稳定调节基金', 549200, 54.92, ''])
    w.writerow(['上年结转收入', 41800, 4.18, ''])
    w.writerow(['收入总量', 4174700, 417.47, ''])
    w.writerow([])
    w.writerow(['一般公共预算支出', 4032900, 403.29, '其中区本级379.62亿'])
    w.writerow(['上解支出', 110000, 11.00, ''])
    w.writerow(['地方政府一般债务还本支出', 31800, 3.18, ''])
    w.writerow(['支出总量', 4174700, 417.47, ''])
    w.writerow([])
    w.writerow(['政府性基金收入合计', 1503066, 150.31, '含土地出让90.08亿+土地收益基金59.92亿'])
    w.writerow(['政府性基金支出合计(估算)', 1628009, 162.80, '城乡社区162.14亿+其他0.66亿, 不含债务还本'])
    w.writerow([])
    w.writerow(['国有资本经营收入合计', 25155, 2.52, ''])
    w.writerow(['国有资本经营支出合计', 22645, 2.27, '含国企资本金注入2.16亿'])
    w.writerow([])

    # 注解
    w.writerow(['【五、注意事项】'])
    w.writerow(['说明'])
    w.writerow(['1. 部门分析数据来源于budget_pdfs_2026目录下各部门/单位2026年预算PDF，提取"财政拨款收入"及相关明细'])
    w.writerow(['2. 总预算草案数据来源于同一目录下的区级总预算PDF（153页），涵盖区本级+镇级+转移支付等全口径'])
    w.writerow(['3. 两者口径不同：部门分析为部门财政拨款支出，总预算含转移支付、债务、稳定调节基金等宏观科目'])
    w.writerow(['4. 教育系统(121所学校)的预算部分包含在区教育局预算中，存在一定重叠'])
    w.writerow(['5. 卫生健康系统中部分社区卫生服务中心预算可能在街镇目录下，也存在交叉'])
    w.writerow(['6. 差异列正值表示部门分析合计 > 总预算对应科目(可能存在口径差异或重叠)'])

print(f"\n对比CSV: {OUT_CSV}")
print(f"  含4个sheet区域: 分目录明细 / 层级汇总 / 总预算对比 / 原文数据")

# 终端快览
print("\n" + "=" * 80)
print("                    与总预算草案对比快览")
print("=" * 80)
print(f"{'项目':20s} | {'部门分析(万元)':>18s} | {'总预算草案(万元)':>18s} | {'差异(万元)':>16s}")
print("-" * 80)
items = [
    ('一般公共预算支出', grand['gg'], master['一般公共预算支出预算']),
    ('政府性基金支出', grand['gf'], master['政府性基金支出预算合计']),
    ('国有资本经营支出', grand['gc'], master['国有资本经营支出合计']),
]
for label, dept_val, master_val in items:
    diff = dept_val - master_val
    print(f"{label:20s} | {dept_val:18,.2f} | {master_val:18,d} | {diff:16,.2f}")
print("-" * 80)
print(f"{'部门分析总计':20s} | {grand['sr']:18,.2f} | {'-':>18s} | {'-':>16s}")
print(f"\n注意: 部门分析合计>总预算草案的原因:")
print(f"  - 教育系统(121校)的预算与区教育局预算存在重叠")
print(f"  - 政府性基金中建管委等含土地出让相关支出，与总预算口径不完全一致")
print(f"  - 总预算草案含债务还本、上解支出、稳定调节基金等非部门分配科目")
