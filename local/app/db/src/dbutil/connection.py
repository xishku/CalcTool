"""Connection 类 —— 封装 sqlite3.Connection，提供便捷的 CRUD 操作"""

import logging
import os
import sqlite3
import time
from contextlib import contextmanager
from typing import Any

from .exceptions import DBConnectionError, DBQueryError
from .migrate import MigrationEngine

logger = logging.getLogger(__name__)


class Connection:
    """封装 sqlite3.Connection，提供 dict 化查询结果、便捷 CRUD 和事务支持。

    用法::

        with Connection("data/mydb.db") as conn:
            rows = conn.fetchall("SELECT * FROM users")
            conn.insert("users", {"name": "Alice", "age": 30})
    """

    def __init__(
        self,
        db_path: str,
        timeout: int = 5,
        migrations: str | None = None,
    ) -> None:
        """初始化连接。

        Args:
            db_path: 数据库文件路径（不存在时自动创建）
            timeout: 连接超时时间（秒）
            migrations: 迁移文件目录路径
        """
        self._path = os.path.abspath(db_path)
        self._timeout = timeout
        self._migrations_dir = migrations
        self._conn: sqlite3.Connection | None = None
        self._opened = False
        self._transaction_depth = 0

    # ── 属性 ──────────────────────────────────────────────

    @property
    def path(self) -> str:
        """数据库文件路径"""
        return self._path

    @property
    def raw(self) -> sqlite3.Connection:
        """获取原生 sqlite3.Connection（供高级用法）"""
        if self._conn is None:
            raise DBConnectionError("数据库未打开，请先调用 open() 或使用 with 语句")
        return self._conn

    # ── 生命周期 ──────────────────────────────────────────

    def open(self) -> "Connection":
        """打开数据库连接，自动创建父目录并执行迁移"""
        if self._opened:
            return self

        parent = os.path.dirname(self._path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)

        try:
            self._conn = sqlite3.connect(self._path, timeout=self._timeout)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        except sqlite3.Error as e:
            raise DBConnectionError(f"无法连接到 {self._path}: {e}") from e

        self._opened = True
        logger.info("数据库已打开: %s", self._path)

        if self._migrations_dir:
            MigrationEngine.apply(self.raw, self._migrations_dir)

        return self

    def close(self) -> None:
        """关闭数据库连接"""
        if self._conn and self._opened:
            try:
                self._conn.close()
            except sqlite3.Error as e:
                logger.warning("关闭数据库时出错: %s", e)
            finally:
                self._conn = None
                self._opened = False
                logger.info("数据库已关闭: %s", self._path)

    def __enter__(self) -> "Connection":
        return self.open()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
        return False

    # ── 查询方法 ──────────────────────────────────────────

    def _ensure_open(self) -> None:
        if self._conn is None:
            raise DBConnectionError("数据库未打开")

    def fetchone(self, sql: str, params: tuple = ()) -> dict | None:
        """查询单行，返回 dict 或 None"""
        self._ensure_open()
        try:
            start = time.perf_counter()
            cursor = self._conn.execute(sql, params)
            row = cursor.fetchone()
            elapsed = (time.perf_counter() - start) * 1000
            logger.debug("SQL(%.1fms): %s | %s", elapsed, sql, params)
            if elapsed > 1000:
                logger.warning("慢查询(%.1fms): %s", elapsed, sql)
            return dict(row) if row else None
        except sqlite3.Error as e:
            raise DBQueryError(f"查询失败: {e}\nSQL: {sql}\nParams: {params}") from e

    def fetchall(self, sql: str, params: tuple = ()) -> list[dict]:
        """查询多行，返回 list[dict]"""
        self._ensure_open()
        try:
            start = time.perf_counter()
            cursor = self._conn.execute(sql, params)
            rows = cursor.fetchall()
            elapsed = (time.perf_counter() - start) * 1000
            logger.debug("SQL(%.1fms): %s | %s", elapsed, sql, params)
            if elapsed > 1000:
                logger.warning("慢查询(%.1fms): %s", elapsed, sql)
            return [dict(r) for r in rows]
        except sqlite3.Error as e:
            raise DBQueryError(f"查询失败: {e}\nSQL: {sql}\nParams: {params}") from e

    # ── 内部辅助 ──────────────────────────────────────────

    def _maybe_commit(self) -> None:
        """仅在没有显式事务时才 commit"""
        if self._transaction_depth == 0:
            self._conn.commit()

    # ── 写操作方法 ────────────────────────────────────────

    def execute(self, sql: str, params: tuple = ()) -> int:
        """执行写操作，返回 affected rows"""
        self._ensure_open()
        try:
            cursor = self._conn.execute(sql, params)
            self._maybe_commit()
            logger.debug("SQL: %s | %s", sql, params)
            return cursor.rowcount
        except sqlite3.Error as e:
            raise DBQueryError(f"执行失败: {e}\nSQL: {sql}\nParams: {params}") from e

    def executemany(self, sql: str, params_list: list[tuple]) -> int:
        """批量执行写操作，返回 affected rows"""
        self._ensure_open()
        try:
            cursor = self._conn.executemany(sql, params_list)
            self._maybe_commit()
            return cursor.rowcount
        except sqlite3.Error as e:
            raise DBQueryError(f"批量执行失败: {e}\nSQL: {sql}") from e

    # ── 便捷 CRUD ────────────────────────────────────────

    def insert(self, table: str, data: dict) -> int:
        """插入一行数据，返回 lastrowid

        Args:
            table: 表名
            data: 列名→值的字典

        Returns:
            新插入行的 rowid
        """
        self._ensure_open()
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        try:
            cursor = self._conn.execute(sql, tuple(data.values()))
            self._maybe_commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            raise DBQueryError(f"插入失败: {e}\nSQL: {sql}") from e

    def insert_many(self, table: str, columns: list[str], rows: list[list]) -> int:
        """批量插入数据

        Args:
            table: 表名
            columns: 列名列表
            rows: 数据行列表，每行为值列表

        Returns:
            影响行数
        """
        self._ensure_open()
        cols = ", ".join(columns)
        placeholders = ", ".join("?" * len(columns))
        sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        try:
            cursor = self._conn.executemany(sql, rows)
            self._maybe_commit()
            return cursor.rowcount
        except sqlite3.Error as e:
            raise DBQueryError(f"批量插入失败: {e}\nSQL: {sql}") from e

    def update(self, table: str, data: dict, where: str, params: tuple = ()) -> int:
        """更新数据

        Args:
            table: 表名
            data: 要更新的列名→值字典
            where: WHERE 子句（不含 WHERE 关键字），如 "id = ?"
            params: WHERE 子句的参数

        Returns:
            影响行数
        """
        self._ensure_open()
        set_clause = ", ".join(f"{k} = ?" for k in data.keys())
        sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
        all_params = tuple(data.values()) + params
        try:
            cursor = self._conn.execute(sql, all_params)
            self._maybe_commit()
            return cursor.rowcount
        except sqlite3.Error as e:
            raise DBQueryError(f"更新失败: {e}\nSQL: {sql}") from e

    def delete(self, table: str, where: str, params: tuple = ()) -> int:
        """删除数据

        Args:
            table: 表名
            where: WHERE 子句（不含 WHERE 关键字），如 "id = ?"
            params: WHERE 子句的参数

        Returns:
            影响行数
        """
        self._ensure_open()
        sql = f"DELETE FROM {table} WHERE {where}"
        try:
            cursor = self._conn.execute(sql, params)
            self._maybe_commit()
            return cursor.rowcount
        except sqlite3.Error as e:
            raise DBQueryError(f"删除失败: {e}\nSQL: {sql}") from e

    # ── 事务支持 ──────────────────────────────────────────

    @contextmanager
    def transaction(self):
        """事务上下文管理器。

        用法::

            with conn.transaction():
                conn.insert("t1", {"val": 1})
                conn.insert("t2", {"val": 2})
            # 块正常退出 → commit
            # 块内抛出异常 → rollback
        """
        self._ensure_open()
        self._transaction_depth += 1
        try:
            self._conn.execute("BEGIN")
            yield
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        finally:
            self._transaction_depth -= 1
