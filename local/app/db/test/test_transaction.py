"""测试事务支持"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dbutil import Connection


@pytest.fixture
def conn():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "txn.db")
        with Connection(db_path) as c:
            c.execute(
                "CREATE TABLE items ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "value INTEGER NOT NULL"
                ")"
            )
            yield c


class TestTransaction:

    def test_commit_on_success(self, conn):
        with conn.transaction():
            conn.insert("items", {"value": 100})
            conn.insert("items", {"value": 200})
        rows = conn.fetchall("SELECT value FROM items ORDER BY id")
        assert len(rows) == 2
        assert rows[0]["value"] == 100
        assert rows[1]["value"] == 200

    def test_rollback_on_error(self, conn):
        with pytest.raises(ValueError):
            with conn.transaction():
                conn.insert("items", {"value": 1})
                conn.insert("items", {"value": 2})
                raise ValueError("模拟异常")
        # 回滚后表中无数据
        rows = conn.fetchall("SELECT * FROM items")
        assert len(rows) == 0

    def test_partial_rollback(self, conn):
        """事务异常后，之前提交的数据不受影响"""
        conn.insert("items", {"value": 999})  # 不在事务内
        with pytest.raises(ValueError):
            with conn.transaction():
                conn.insert("items", {"value": 1})
                raise ValueError("rollback")
        rows = conn.fetchall("SELECT value FROM items")
        assert len(rows) == 1
        assert rows[0]["value"] == 999
