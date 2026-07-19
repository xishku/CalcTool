"""
基金每日净值查询脚本

从 SQLite 数据库读取已存储的基金净值数据，
支持自定义基金代码、日期区间、分页显示。

用法:
    python query_nav.py                 # 打印 001438 全部数据
    python query_nav.py 001438          # 等价于上面
    python query_nav.py 001438 -s 2026-01-01   # 从指定日期开始
    python query_nav.py 001438 2026-01-01 2026-06-30  # 日期区间
    python query_nav.py --db ../fund_nav.db --list    # 列出所有基金
    python query_nav.py --list                        # 列出当前数据库中的基金

════════════════════════════════════════════════════════
  用户可以修改下面 CONFIG 块中的默认值来定制行为
════════════════════════════════════════════════════════
"""

import os
import sys

# ─── 用户可配置区域 ──────────────────────────────────────

# 数据库文件路径（默认：与本脚本同目录的 fund_nav.db）
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fund_nav.db")

# 默认查询的基金代码
DEFAULT_FUND_CODE = "001438"

# 日期区间（留空 = 全部），格式 YYYY-MM-DD
START_DATE = ""          # 例如 "2025-01-01"
END_DATE = ""            # 例如 "2025-12-31"

# 打印设置
HEAD_LINES = 20          # 开头打印多少行
TAIL_LINES = 10          # 末尾打印多少行
PAGE_SIZE = 40           # 使用 --all 分页时每页行数

# ─── 内部逻辑（一般无需修改）─────────────────────────────


def get_fdn(db_path=None):
    """延迟导入 FundDailyNAV，避免启动失败"""
    _db = db_path or DB_PATH
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from fund_daily_nav import FundDailyNAV
    return FundDailyNAV(db_path=_db)


def format_row(r):
    """格式化一行净值数据"""
    date = r["nav_date"]
    unit = f"{r['unit_nav']:.4f}" if r["unit_nav"] is not None else "-"
    cum = f"{r['cumulative_nav']:.4f}" if r["cumulative_nav"] is not None else "-"
    return f"  {date}  单位: {unit}  累计: {cum}"


def print_table(rows, start=0, count=None):
    """打印表格"""
    if not rows:
        print("  (无数据)")
        return
    end = start + count if count else len(rows)
    subset = rows[start:end]
    # 检查是否有 daily_return 字段
    has_return = any(
        r.get("daily_return") is not None for r in subset
    )
    if has_return:
        print(f"  {'日期':<14} {'单位净值':>10} {'累计净值':>10} {'日收益':>8}")
        print(f"  {'-'*14} {'-'*10} {'-'*10} {'-'*8}")
        for r in subset:
            unit = f"{r['unit_nav']:.4f}" if r['unit_nav'] is not None else "-"
            cum = f"{r['cumulative_nav']:.4f}" if r['cumulative_nav'] is not None else "-"
            ret = f"{r['daily_return']:+.2f}%" if r.get('daily_return') is not None else "-"
            print(f"  {r['nav_date']:<14} {unit:>10} {cum:>10} {ret:>8}")
    else:
        print(f"  {'日期':<14} {'单位净值':>10} {'累计净值':>10}")
        print(f"  {'-'*14} {'-'*10} {'-'*10}")
        for r in subset:
            unit = f"{r['unit_nav']:.4f}" if r['unit_nav'] is not None else "-"
            cum = f"{r['cumulative_nav']:.4f}" if r['cumulative_nav'] is not None else "-"
            print(f"  {r['nav_date']:<14} {unit:>10} {cum:>10}")


def show_stats(rows):
    """计算并打印统计信息"""
    unit_vals = [r["unit_nav"] for r in rows if r["unit_nav"] is not None]
    if not unit_vals:
        return

    min_val = min(unit_vals)
    max_val = max(unit_vals)
    first_val = unit_vals[0]
    last_val = unit_vals[-1]
    total_return = (last_val / first_val - 1) * 100 if first_val else 0

    # 找极值日期
    min_row = next(r for r in rows if r["unit_nav"] == min_val)
    max_row = next(r for r in rows if r["unit_nav"] == max_val)

    print(f"\n  {'='*45}")
    print(f"  统计概览")
    print(f"  {'='*45}")
    print(f"  日期范围     : {rows[0]['nav_date']} ~ {rows[-1]['nav_date']}")
    print(f"  总记录数     : {len(rows)}")
    print(f"  区间收益率   : {total_return:+.2f}%")
    print(f"  最低净值     : {min_val:.4f}  ({min_row['nav_date']})")
    print(f"  最高净值     : {max_val:.4f}  ({max_row['nav_date']})")
    print(f"  最新净值     : {last_val:.4f}  ({rows[-1]['nav_date']})")

    # 日收益率统计（如有）
    ret_vals = [r["daily_return"] for r in rows
                if r.get("daily_return") is not None]
    if ret_vals:
        avg_ret = sum(ret_vals) / len(ret_vals)
        up_days = sum(1 for v in ret_vals if v > 0)
        down_days = sum(1 for v in ret_vals if v < 0)
        max_up = max(ret_vals)
        max_down = min(ret_vals)
        max_up_row = next(r for r in rows if r.get("daily_return") == max_up)
        max_down_row = next(r for r in rows if r.get("daily_return") == max_down)
        print(f"  日收益统计   :")
        print(f"    均收益     : {avg_ret:+.2f}%")
        print(f"    上涨天数   : {up_days}  ({up_days/len(ret_vals)*100:.1f}%)")
        print(f"    下跌天数   : {down_days}  ({down_days/len(ret_vals)*100:.1f}%)")
        print(f"    最大单日涨幅: {max_up:+.2f}%  ({max_up_row['nav_date']})")
        print(f"    最大单日跌幅: {max_down:+.2f}%  ({max_down_row['nav_date']})")


def show_fund_list(fdn):
    """列出数据库中所有基金"""
    meta_list = fdn.query_meta()
    if not meta_list:
        print("数据库中没有任何基金数据。")
        return
    print(f"\n{'代码':<8} {'名称':<30} {'起始日期':<12} {'最新日期':<12} {'记录数':>6}")
    print("-" * 72)
    for m in meta_list:
        name = (m.get("fund_name") or "")[:28]
        print(f"  {m['fund_code']:<8} {name:<30} {m.get('first_date','') or '-':<12} "
              f"{m.get('last_date','') or '-':<12} {m.get('record_count',0):>6}")
    print(f"\n共 {len(meta_list)} 只基金")


def main():
    # 解析命令行参数
    args = sys.argv[1:]

    fund_code = DEFAULT_FUND_CODE
    fund_code_set = False       # 是否通过命令行指定了基金代码
    start_date = START_DATE or None
    end_date = END_DATE or None
    db_path = DB_PATH
    show_all = False
    list_funds = False
    no_stats = False

    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-h", "--help"):
            print(__doc__)
            return
        elif a == "--list":
            list_funds = True
        elif a == "--all":
            show_all = True
        elif a == "--no-stats":
            no_stats = True
        elif a in ("-s", "--start"):
            i += 1
            if i < len(args):
                start_date = args[i]
        elif a in ("-e", "--end"):
            i += 1
            if i < len(args):
                end_date = args[i]
        elif a == "--db":
            i += 1
            if i < len(args):
                db_path = args[i]
        elif not a.startswith("-"):
            # 位置参数：基金代码(6位数字)、起始日期、结束日期
            if not fund_code_set and len(a) == 6 and a.isdigit():
                fund_code = a
                fund_code_set = True
            elif start_date is None:
                start_date = a
            elif end_date is None:
                end_date = a
        i += 1

    # 初始化
    print(f"数据库: {os.path.abspath(db_path)}")
    fdn = get_fdn(db_path)

    # --list 模式：列出所有基金
    if list_funds:
        show_fund_list(fdn)
        return

    # 查询
    print(f"\n{'='*50}")
    print(f"  基金净值查询")
    print(f"{'='*50}")

    rows = fdn.query_nav(fund_code, start_date=start_date, end_date=end_date)
    if not rows:
        print(f"\n基金 {fund_code} 无数据。可能的原因：")
        print(f"  1. 该基金尚未爬取 → python fund_daily_nav.py --test {fund_code}")
        print(f"  2. 数据库路径不对 → --db 指定路径")
        print(f"  3. 先用 --list 查看已有基金")
        return

    # 打印元信息
    meta_list = fdn.query_meta(fund_code)
    if meta_list:
        m = meta_list[0]
        print(f"  基金: {m.get('fund_name', fund_code)} ({fund_code})")
        print(f"  区间: {m.get('first_date','')} ~ {m.get('last_date','')} "
              f"({m.get('record_count', len(rows))} 条)")

    # --all 模式：分页全部打印
    if show_all:
        total = len(rows)
        page = 0
        while page * PAGE_SIZE < total:
            start = page * PAGE_SIZE
            end = min(start + PAGE_SIZE, total)
            print(f"\n  --- 第 {page+1} 页 ({start+1}-{end}/{total}) ---")
            print_table(rows, start=start, count=PAGE_SIZE)
            if end >= total:
                break
            try:
                input(f"\n  [回车继续下一页 (q=退出)] ")
            except EOFError:
                break
    else:
        # 默认模式：头 + 尾
        print(f"\n  --- 前 {min(HEAD_LINES, len(rows))} 条 ---")
        print_table(rows, start=0, count=HEAD_LINES)

        if len(rows) > HEAD_LINES + TAIL_LINES:
            print(f"\n  ... 省略 {len(rows) - HEAD_LINES - TAIL_LINES} 条 ...")
            print(f"\n  --- 后 {TAIL_LINES} 条 ---")
            print_table(rows, start=-TAIL_LINES, count=TAIL_LINES)
        elif len(rows) > HEAD_LINES:
            print(f"\n  --- 后 {len(rows) - HEAD_LINES} 条 ---")
            print_table(rows, start=HEAD_LINES)

    # 统计
    if not no_stats:
        show_stats(rows)

    print(f"\n提示: python query_nav.py --list    查看所有基金")
    print(f"      python query_nav.py --all      分页查看全部记录")
    print(f"      python query_nav.py {fund_code} 2025-01-01 2025-12-31  指定区间")


if __name__ == "__main__":
    main()
