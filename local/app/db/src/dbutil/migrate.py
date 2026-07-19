"""Schema 迁移引擎"""

import logging
import os
import re
import sqlite3

from .exceptions import DBMigrationError

logger = logging.getLogger(__name__)

# 迁移文件名格式: 001_name.sql, 002_name.sql ...
_MIGRATION_PATTERN = re.compile(r"^(\d{3,})_.+\.sql$")


class MigrationEngine:
    """基于 SQL 文件的 Schema 版本迁移引擎。

    在目标数据库维护 ``_schema_version`` 表，记录已执行的迁移版本号。
    迁移文件按文件名前缀数字升序依次执行，只执行未应用的新版本。
    """

    _VERSION_TABLE = "_schema_version"

    @classmethod
    def apply(cls, conn: sqlite3.Connection, migrations_dir: str) -> int:
        """执行迁移。

        Args:
            conn: 原生 sqlite3.Connection
            migrations_dir: 迁移 SQL 文件所在目录

        Returns:
            新执行的迁移文件数量
        """
        cls._ensure_version_table(conn)
        applied = cls._get_applied_versions(conn)

        if not os.path.isdir(migrations_dir):
            logger.info("迁移目录不存在，跳过: %s", migrations_dir)
            return 0

        files = sorted(cls._list_migration_files(migrations_dir))
        new_count = 0

        for version, filename, filepath in files:
            if version in applied:
                continue

            sql_content = cls._read_sql(filepath)
            logger.info("执行迁移 %s: %s", version, filename)
            try:
                conn.executescript(sql_content)
                conn.execute(
                    f"INSERT INTO {cls._VERSION_TABLE} (version, filename) VALUES (?, ?)",
                    (version, filename),
                )
                conn.commit()
                new_count += 1
                logger.info("迁移完成: %s", filename)
            except sqlite3.Error as e:
                conn.rollback()
                raise DBMigrationError(
                    f"迁移 {version} 失败: {filename}\n{e}"
                ) from e

        if new_count:
            logger.info("共执行 %d 个迁移", new_count)
        return new_count

    @classmethod
    def _ensure_version_table(cls, conn: sqlite3.Connection) -> None:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {cls._VERSION_TABLE} (
                version     TEXT PRIMARY KEY,
                filename    TEXT NOT NULL,
                applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()

    @classmethod
    def _get_applied_versions(cls, conn: sqlite3.Connection) -> set[str]:
        cursor = conn.execute(f"SELECT version FROM {cls._VERSION_TABLE}")
        return {row[0] for row in cursor.fetchall()}

    @staticmethod
    def _list_migration_files(directory: str) -> list[tuple[str, str, str]]:
        """扫描迁移文件列表，返回 [(version, filename, fullpath), ...]"""
        results = []
        for fname in os.listdir(directory):
            match = _MIGRATION_PATTERN.match(fname)
            if match:
                results.append(
                    (match.group(1), fname, os.path.join(directory, fname))
                )
        return results

    @staticmethod
    def _read_sql(filepath: str) -> str:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
