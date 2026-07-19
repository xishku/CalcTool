"""
基金每日净值爬取与存储模块

数据源：天天基金 (fund.eastmoney.com)
- pingzhongdata/{code}.js → 全量历史单位净值 + 累计净值 + 日收益率（一次请求）

存储：SQLite（通过 dbutil 模块）

与同花顺(10jqka)相比的优势：
- 标准 requests，无需 curl_cffi 反爬
- 单次请求获取全部历史数据（无需分页）
- 限流宽松，可高并发（10-20 workers）
- 自带日收益率数据
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

# 中国时区偏移
_UTC8 = timezone(timedelta(hours=8))

# ─── 请求头 ──────────────────────────────────────────────

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "http://fund.eastmoney.com/",
}

_PINGZHONG_URL = "http://fund.eastmoney.com/pingzhongdata/{code}.js"


class FundDailyNAV:
    """基金每日净值数据爬取与存储。

    用法::

        fdn = FundDailyNAV()

        # 测试：单只基金
        fdn.fetch_and_store_one("001438")

        # 批量：全部基金（天天基金限流宽松，可用 10-20 并发）
        fdn.fetch_and_store_all(max_workers=10)
    """

    def __init__(self, db_path: str = "fund_nav.db"):
        sys.path.insert(
            0,
            os.path.join(
                os.path.dirname(__file__),
                "..", "..", "..", "..", "local", "app", "db", "src",
            ),
        )
        from dbutil import Connection

        self._db_path = os.path.abspath(db_path)
        self._Connection = Connection
        self._open_db()

    # ─── 数据库初始化 ────────────────────────────────────

    def _open_db(self):
        """打开数据库并建表（首次自动创建）。兼容旧表结构自动升级。"""
        conn = self._Connection(self._db_path).open()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fund_daily_nav (
                fund_code      TEXT NOT NULL,
                nav_date       TEXT NOT NULL,
                unit_nav       REAL,
                cumulative_nav REAL,
                PRIMARY KEY (fund_code, nav_date)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fund_nav_meta (
                fund_code    TEXT PRIMARY KEY,
                fund_name    TEXT,
                first_date   TEXT,
                last_date    TEXT,
                record_count INTEGER,
                updated_at   TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_nav_code ON fund_daily_nav(fund_code)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_nav_date ON fund_daily_nav(nav_date)")

        # 升级：尝试添加 daily_return 列（兼容旧数据库）
        try:
            conn.execute(
                "ALTER TABLE fund_daily_nav ADD COLUMN daily_return REAL")
        except Exception:
            pass  # 列已存在

        conn.close()

    def _get_conn(self):
        return self._Connection(self._db_path).open()

    # ─── 核心：天天基金净值获取 ──────────────────────────

    @staticmethod
    def _ts_to_date(ts_ms: int) -> str:
        """UTC 毫秒时间戳 → YYYY-MM-DD（北京时间）"""
        if not ts_ms:
            return ""
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        return dt.astimezone(_UTC8).strftime("%Y-%m-%d")

    @staticmethod
    def _extract_js_json(text: str, var_name: str) -> Optional[list]:
        """从 JS 文本中提取 JSON 数组变量。"""
        # Data_netWorthTrend 是对象数组 [{x, y, ...}]
        # Data_ACWorthTrend 是二维数组 [[ts, val], ...]
        pattern = rf"{var_name}\s*=\s*(\[.*?\])\s*;"
        m = re.search(pattern, text, re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _extract_js_string(text: str, var_name: str) -> str:
        """从 JS 文本中提取字符串变量，如 fS_name = \"xxx\";"""
        m = re.search(rf'{var_name}\s*=\s*"([^"]*)"', text)
        return m.group(1) if m else ""

    def _fetch_nav_from_eastmoney(self, code: str) -> Optional[dict]:
        """从天天基金获取一只基金的全量历史净值。

        Returns:
            {
                "fund_code": "001438",
                "fund_name": "易方达瑞享混合E",
                "nav_data": [
                    ("2020-07-07", 1.0000, 1.0000, 0.50),
                    # (date, unit_nav, cumulative_nav, daily_return%)
                ]
            }
            失败返回 None
        """
        url = _PINGZHONG_URL.format(code=code)
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=15)
            if resp.status_code != 200:
                return None
            resp.encoding = "utf-8"
            text = resp.text
        except Exception:
            return None

        # 提取单位净值走势
        unit_data = self._extract_js_json(text, "Data_netWorthTrend")
        if not unit_data:
            return None

        # 提取累计净值走势（按时间戳建立索引）
        cum_data = self._extract_js_json(text, "Data_ACWorthTrend")
        cum_map = {}
        if cum_data:
            cum_map = {item[0]: item[1] for item in cum_data if len(item) >= 2}

        # 提取基金名称
        fund_name = self._extract_js_string(text, "fS_name")

        # 合并：日期、单位净值、累计净值、日收益率
        nav_data = []
        for item in unit_data:
            ts = item.get("x", 0)
            if not ts:
                continue
            date_str = self._ts_to_date(ts)
            unit_nav = item.get("y")
            cum_nav = cum_map.get(ts)
            daily_return = item.get("equityReturn", 0)
            nav_data.append((date_str, unit_nav, cum_nav, daily_return))

        if not nav_data:
            return None

        return {
            "fund_code": code,
            "fund_name": fund_name,
            "nav_data": nav_data,
        }

    # ─── 存储 ────────────────────────────────────────────

    def store_nav_data(self, fund_code: str, nav_data: list,
                       fund_name: str = "", incremental: bool = False) -> int:
        """将净值数据存入数据库（事务批量写入，幂等）。

        Args:
            fund_code: 基金代码
            nav_data: [(date, unit_nav, cumulative_nav, daily_return), ...]
            fund_name: 基金名称
            incremental: True=只插入新记录（INSERT OR IGNORE），
                         False=全量替换（DELETE + INSERT）

        Returns:
            写入的记录数
        """
        if not nav_data:
            return 0

        with self._get_conn() as conn:
            with conn.transaction():
                if incremental:
                    # 增量模式：INSERT OR IGNORE 跳过已有主键
                    rows = [(fund_code, d, u, c, r)
                            for d, u, c, r in nav_data]
                    import sqlite3
                    raw = conn.raw
                    try:
                        raw.executemany(
                            "INSERT OR IGNORE INTO fund_daily_nav "
                            "(fund_code, nav_date, unit_nav, "
                            "cumulative_nav, daily_return) "
                            "VALUES (?, ?, ?, ?, ?)",
                            rows)
                        inserted = raw.changes  # IGNORE 时返回实际插入行数
                    except sqlite3.Error as e:
                        raise Exception(f"增量插入失败: {e}")
                else:
                    # 全量替换
                    conn.delete("fund_daily_nav",
                                "fund_code = ?", (fund_code,))
                    rows = [[fund_code, d, u, c, r]
                            for d, u, c, r in nav_data]
                    inserted = conn.insert_many(
                        "fund_daily_nav",
                        ["fund_code", "nav_date", "unit_nav",
                         "cumulative_nav", "daily_return"],
                        rows,
                    )

                # 更新 meta：用数据库实际数据计算首尾日期和记录数
                meta = conn.fetchone(
                    "SELECT MIN(nav_date) as first_dt, "
                    "MAX(nav_date) as last_dt, COUNT(*) as cnt "
                    "FROM fund_daily_nav WHERE fund_code = ?",
                    (fund_code,))
                conn.execute("""
                    INSERT OR REPLACE INTO fund_nav_meta
                        (fund_code, fund_name, first_date, last_date,
                         record_count, updated_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                """, (fund_code, fund_name,
                      meta["first_dt"], meta["last_dt"], meta["cnt"]))

        return inserted

    def get_latest_date(self, fund_code: str) -> Optional[str]:
        """获取某基金在库中的最新净值日期。"""
        with self._get_conn() as conn:
            row = conn.fetchone(
                "SELECT MAX(nav_date) as dt FROM fund_daily_nav "
                "WHERE fund_code = ?",
                (fund_code,))
            return row["dt"] if row else None

    # ─── 公开 API ────────────────────────────────────────

    def fetch_and_store_one(self, code: str) -> bool:
        """获取并存储单只基金的完整历史净值。"""
        print(f"\n[每日净值] 获取 {code} ...")
        result = self._fetch_nav_from_eastmoney(code)
        if not result:
            print(f"  {code} 无数据，跳过")
            return False

        nav_data = result["nav_data"]
        fund_name = result.get("fund_name", "")
        date_range = f"{nav_data[0][0]} ~ {nav_data[-1][0]}"
        print(f"  {fund_name} | {len(nav_data)} 条 | {date_range}")

        count = self.store_nav_data(code, nav_data, fund_name)
        print(f"  写入 {count} 条到数据库")
        return True

    def fetch_and_store_all(self, max_workers: int = 10, batch_size: int = 0,
                            resume: bool = False, update: bool = False
                            ) -> dict:
        """批量获取并存储全部基金的每日净值。

        Args:
            max_workers: 并发线程数（天天基金限流宽松，建议 10-20）
            batch_size: 只处理前 N 只，0 = 全部
            resume: 断点续传（首次构建用），跳过已有数据的基金
            update: 增量更新（日常用），只插入比库中最新日期更新的记录

        Returns:
            {"success", "failed", "skipped", "updated", "total"}
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from fund_list import FundList

        # 获取基金列表
        fund_codes = []
        print("[每日净值] 正在加载基金列表...")
        for fund in FundList().get_fund_structured_list():
            fund_codes.append(fund["code"])

        total_available = len(fund_codes)
        skipped = 0

        mode_label = "增量更新" if update else "断点续传" if resume else "全量"

        if resume or update:
            # 构建已有基金及其最新日期映射
            existing_map = {}  # fund_code -> last_date
            with self._get_conn() as conn:
                rows = conn.fetchall(
                    "SELECT fund_code, last_date FROM fund_nav_meta")

            if resume:
                # 断点续传：跳过整个基金
                existing = {r["fund_code"] for r in rows}
                new_codes = [c for c in fund_codes if c not in existing]
                skipped = len(fund_codes) - len(new_codes)
                fund_codes = new_codes
            elif update:
                # 增量更新：保留已有基金，但只插新数据
                existing_map = {r["fund_code"]: r["last_date"] for r in rows}
                empty_count = sum(1 for c in fund_codes
                                  if c not in existing_map)
                if empty_count:
                    print(f"[每日净值] 增量更新: {empty_count} 只基金无数据"
                          f"（将全量获取），{len(existing_map)} 只有数据"
                          f"（仅插入增量）")
                else:
                    print(f"[每日净值] 增量更新: {len(existing_map)} 只基金"
                          f" 将只插入新日期数据")
            print(f"[每日净值] {mode_label}: 需处理 {len(fund_codes)} 只")

        if batch_size > 0:
            fund_codes = fund_codes[:batch_size]

        print(f"\n[每日净值] 开始获取 {len(fund_codes)} 只基金 "
              f"(共 {total_available} 只，{max_workers} 并发)...")

        success = 0
        failed = 0
        updated = 0     # 增量模式下有新增数据的数量
        no_change = 0   # 增量模式下无新增的数量
        lock = threading.Lock()
        start_time = time.time()

        def _worker(code: str):
            nonlocal success, failed, updated, no_change
            result = self._fetch_nav_from_eastmoney(code)
            if not result:
                with lock:
                    failed += 1
                return

            nav_data = result["nav_data"]
            fund_name = result.get("fund_name", "")

            if update and code in existing_map:
                # 增量模式：只取比库中最新的日期更新的记录
                last_db_date = existing_map[code]
                new_data = [(d, u, c, r) for d, u, c, r in nav_data
                            if d > last_db_date]
                if not new_data:
                    with lock:
                        no_change += 1
                    return
                self.store_nav_data(code, new_data, fund_name,
                                    incremental=True)
                with lock:
                    updated += 1
            else:
                # 全量 / resume 模式
                self.store_nav_data(code, nav_data, fund_name)
                with lock:
                    success += 1

            with lock:
                done = success + failed + updated + no_change
                if done % 100 == 0 or done == len(fund_codes):
                    elapsed = time.time() - start_time
                    rate = done / elapsed if elapsed > 0 else 0
                    eta = (len(fund_codes) - done) / rate if rate > 0 else 0
                    parts = []
                    if update:
                        parts.append(f"新增 {updated}, 无变化 {no_change}")
                    parts.append(f"成功 {success}, 失败 {failed}")
                    print(f"  进度: {done}/{len(fund_codes)} "
                          f"({' | '.join(parts)}) "
                          f"[{rate:.1f}只/s, 预计剩余 {eta/60:.0f}min]")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_worker, c): c for c in fund_codes}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass

        elapsed = time.time() - start_time
        done = success + failed + updated + no_change
        parts = [f"耗时 {elapsed/60:.1f} 分钟"]
        if update:
            parts.append(f"新增数据 {updated}")
            parts.append(f"无变化 {no_change}")
        parts.append(f"全量成功 {success}")
        parts.append(f"失败 {failed}")
        parts.append(f"跳过 {skipped}")
        print(f"\n[每日净值] 完成! {' | '.join(parts)}")
        return {"success": success, "failed": failed, "skipped": skipped,
                "updated": updated, "no_change": no_change,
                "total": len(fund_codes)}

    # ─── 查询 ────────────────────────────────────────────

    def query_nav(self, fund_code: str, start_date: str = None,
                  end_date: str = None) -> list:
        """查询指定基金的净值数据。"""
        with self._get_conn() as conn:
            if start_date and end_date:
                return conn.fetchall(
                    "SELECT nav_date, unit_nav, cumulative_nav, daily_return "
                    "FROM fund_daily_nav "
                    "WHERE fund_code = ? AND nav_date >= ? AND nav_date <= ? "
                    "ORDER BY nav_date",
                    (fund_code, start_date, end_date),
                )
            elif start_date:
                return conn.fetchall(
                    "SELECT nav_date, unit_nav, cumulative_nav, daily_return "
                    "FROM fund_daily_nav "
                    "WHERE fund_code = ? AND nav_date >= ? "
                    "ORDER BY nav_date",
                    (fund_code, start_date),
                )
            else:
                return conn.fetchall(
                    "SELECT nav_date, unit_nav, cumulative_nav, daily_return "
                    "FROM fund_daily_nav "
                    "WHERE fund_code = ? ORDER BY nav_date",
                    (fund_code,),
                )

    def query_meta(self, fund_code: str = None) -> list:
        """查询基金元信息。"""
        with self._get_conn() as conn:
            if fund_code:
                return conn.fetchall(
                    "SELECT * FROM fund_nav_meta WHERE fund_code = ?",
                    (fund_code,))
            return conn.fetchall(
                "SELECT * FROM fund_nav_meta ORDER BY fund_code")

    def stats(self) -> dict:
        """统计概览"""
        with self._get_conn() as conn:
            total = conn.fetchone("SELECT COUNT(*) as cnt FROM fund_daily_nav")
            funds = conn.fetchone("SELECT COUNT(*) as cnt FROM fund_nav_meta")
            latest = conn.fetchone(
                "SELECT MAX(nav_date) as dt FROM fund_daily_nav")
        return {
            "total_records": total["cnt"] if total else 0,
            "total_funds": funds["cnt"] if funds else 0,
            "latest_date": latest["dt"] if latest else None,
        }


# ─── 命令行入口 ─────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="基金每日净值爬取工具（天天基金数据源）")
    parser.add_argument("--test", type=str, default=None,
                        help="测试单只基金，如 --test 001438")
    parser.add_argument("--all", action="store_true",
                        help="批量获取全部基金")
    parser.add_argument("--batch", type=int, default=0,
                        help="只获取前 N 只基金（0=全部）")
    parser.add_argument("--resume", action="store_true",
                        help="断点续传：跳过已有数据的基金（首次构建用）")
    parser.add_argument("--update", action="store_true",
                        help="增量更新：只插入比库中更新的净值记录（日常更新用）")
    parser.add_argument("--workers", type=int, default=10,
                        help="并发线程数（默认 10）")
    parser.add_argument("--stats", action="store_true",
                        help="显示统计概览")
    parser.add_argument("--query", type=str, default=None,
                        help="查询基金净值，如 --query 001438")
    parser.add_argument("--db", type=str, default="fund_nav.db",
                        help="数据库路径")

    args = parser.parse_args()
    fdn = FundDailyNAV(db_path=args.db)

    if args.test:
        fdn.fetch_and_store_one(args.test)
    elif args.all:
        fdn.fetch_and_store_all(max_workers=args.workers,
                                batch_size=args.batch,
                                resume=args.resume,
                                update=args.update)
    elif args.stats:
        s = fdn.stats()
        print(f"总记录: {s['total_records']}")
        print(f"总基金: {s['total_funds']}")
        print(f"最新日期: {s['latest_date']}")
    elif args.query:
        rows = fdn.query_nav(args.query)
        meta_list = fdn.query_meta(args.query)
        if meta_list:
            m = meta_list[0]
            print(f"基金: {m['fund_name']} ({m['fund_code']})")
            print(f"区间: {m['first_date']} ~ {m['last_date']} "
                  f"({m['record_count']} 条)")
        print(f"\n最近 5 条净值:")
        for r in rows[-5:]:
            cum_str = (f"  累计: {r['cumulative_nav']:.4f}"
                       if r['cumulative_nav'] else "")
            ret_str = (f"  日收益: {r['daily_return']:+.2f}%"
                       if r['daily_return'] is not None else "")
            print(f"  {r['nav_date']}  单位: {r['unit_nav']:.4f}"
                  f"{cum_str}{ret_str}")
    else:
        parser.print_help()
