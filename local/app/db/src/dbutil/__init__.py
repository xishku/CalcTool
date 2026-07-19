"""dbutil —— 轻量级 SQLite 数据库访问接口

用法::

    from dbutil import DB

    # 直接按路径打开
    with DB.open("data/mydb.db") as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)")
        conn.insert("users", {"name": "Alice"})
        rows = conn.fetchall("SELECT * FROM users")

    # 按配置名称打开（需先配置 db_config.yaml）
    # with DB.get("leetcode") as conn:
    #     rows = conn.fetchall("SELECT * FROM submissions")

"""

import csv
import json
import logging
import os

from .connection import Connection
from .exceptions import DBConnectionError, DBError, DBMigrationError, DBQueryError
from .manager import DBManager

logger = logging.getLogger(__name__)


class _DB:
    """统一入口命名空间。

    提供静态方法：
    - ``DB.open(path, **kwargs)`` → Connection（直接按路径）
    - ``DB.get(name)`` → Connection（按配置名称）
    - ``DB.export_csv(rows, filepath)``
    - ``DB.export_json(rows, filepath)``
    """

    _manager: DBManager | None = None

    @staticmethod
    def open(
        db_path: str,
        timeout: int = 5,
        migrations: str | None = None,
    ) -> Connection:
        """按路径打开/创建数据库。

        Args:
            db_path: .db 文件路径（相对路径基于当前工作目录）
            timeout: 连接超时（秒）
            migrations: 迁移文件目录

        Returns:
            Connection 实例（需 open() 或 with 语句）
        """
        return Connection(
            db_path=db_path,
            timeout=timeout,
            migrations=migrations,
        )

    @classmethod
    def get(cls, name: str, config_path: str = "db_config.yaml") -> Connection:
        """按配置名称获取数据库连接。

        需要同目录下有 ``db_config.yaml`` 配置文件。

        Args:
            name: 数据库配置名称
            config_path: 配置文件路径

        Returns:
            Connection 实例
        """
        if cls._manager is None:
            cls._manager = DBManager.load(config_path)
        return cls._manager.get(name)

    @classmethod
    def list_databases(cls, config_path: str = "db_config.yaml") -> list[str]:
        """列出所有已配置的数据库名称"""
        if cls._manager is None:
            cls._manager = DBManager.load(config_path)
        return cls._manager.list_names()

    @staticmethod
    def export_csv(rows: list[dict], filepath: str) -> None:
        """将查询结果导出为 CSV 文件。

        Args:
            rows: fetchall() 返回的 dict 列表
            filepath: 输出路径
        """
        if not rows:
            logger.warning("导出 CSV: 无数据，仍创建文件头部")
        parent = os.path.dirname(filepath)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys() if rows else [])
            writer.writeheader()
            writer.writerows(rows)
        logger.info("已导出 %d 行到 %s", len(rows), filepath)

    @staticmethod
    def export_json(rows: list[dict], filepath: str) -> None:
        """将查询结果导出为 JSON 文件。

        Args:
            rows: fetchall() 返回的 dict 列表
            filepath: 输出路径
        """
        parent = os.path.dirname(filepath)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2, default=str)
        logger.info("已导出 %d 行到 %s", len(rows), filepath)

    @classmethod
    def reset(cls) -> None:
        """重置 DBManager 单例（主要用于测试）"""
        cls._manager = None
        DBManager.reset()


# 公开 API
DB = _DB()

__all__ = [
    "DB",
    "Connection",
    "DBError",
    "DBConnectionError",
    "DBQueryError",
    "DBMigrationError",
]
