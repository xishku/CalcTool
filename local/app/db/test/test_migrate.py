"""测试 Schema 迁移引擎"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dbutil import Connection, DBMigrationError


@pytest.fixture
def migration_dir():
    """创建包含多个迁移文件的临时目录"""
    with tempfile.TemporaryDirectory() as mdir:
        # 001: 建表
        with open(os.path.join(mdir, "001_init.sql"), "w") as f:
            f.write("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    name TEXT
                );
            """)
        # 002: 加列
        with open(os.path.join(mdir, "002_add_email.sql"), "w") as f:
            f.write("ALTER TABLE users ADD COLUMN email TEXT;")
        yield mdir


class TestMigration:

    def test_apply_all_migrations(self, migration_dir):
        """首次打开时执行所有迁移"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "migrate.db")
            with Connection(db_path, migrations=migration_dir) as conn:
                # 验证表结构
                conn.insert("users", {"id": 1, "name": "Alice", "email": "a@x.com"})
                row = conn.fetchone("SELECT * FROM users WHERE id = 1")
                assert row["name"] == "Alice"
                assert row["email"] == "a@x.com"

    def test_skip_applied_migrations(self, migration_dir):
        """再次打开时跳过已执行的迁移"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "migrate2.db")
            with Connection(db_path, migrations=migration_dir) as conn:
                conn.insert("users", {"id": 1, "name": "A"})

            # 再次打开，不应报错
            with Connection(db_path, migrations=migration_dir) as conn:
                rows = conn.fetchall("SELECT * FROM users")
                assert len(rows) == 1

    def test_no_migrations_dir_skips(self):
        """迁移目录不存在时正常跳过"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "nomig.db")
            with Connection(db_path, migrations="/nonexistent/dir") as conn:
                conn.execute("CREATE TABLE t (id INTEGER)")
                conn.insert("t", {"id": 1})
                assert conn.fetchone("SELECT * FROM t")["id"] == 1

    def test_bad_sql_raises_migration_error(self):
        """迁移文件含错误 SQL 时抛出 DBMigrationError"""
        with tempfile.TemporaryDirectory() as mdir:
            with open(os.path.join(mdir, "001_bad.sql"), "w") as f:
                f.write("INVALID SQL STATEMENT;")

            with tempfile.TemporaryDirectory() as tmp:
                db_path = os.path.join(tmp, "bad.db")
                with pytest.raises(DBMigrationError):
                    Connection(db_path, migrations=mdir).open()
