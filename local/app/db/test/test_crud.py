"""测试 CRUD 操作：insert / insert_many / fetchone / fetchall / update / delete"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dbutil import Connection


@pytest.fixture
def conn():
    """创建临时数据库并建表"""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "crud.db")
        with Connection(db_path) as c:
            c.execute(
                "CREATE TABLE users ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "name TEXT NOT NULL,"
                "age INTEGER DEFAULT 0"
                ")"
            )
            yield c
        # tmp 目录自动清理


class TestInsert:

    def test_insert_returns_lastrowid(self, conn):
        rid = conn.insert("users", {"name": "Alice", "age": 30})
        assert rid == 1

    def test_insert_many(self, conn):
        rows = [
            ["Alice", 30],
            ["Bob", 25],
            ["Charlie", 35],
        ]
        count = conn.insert_many("users", ["name", "age"], rows)
        assert count == 3

        result = conn.fetchall("SELECT name FROM users ORDER BY id")
        assert [r["name"] for r in result] == ["Alice", "Bob", "Charlie"]


class TestQuery:

    def test_fetchone_returns_dict(self, conn):
        conn.insert("users", {"name": "Alice", "age": 30})
        row = conn.fetchone("SELECT * FROM users WHERE id = ?", (1,))
        assert isinstance(row, dict)
        assert row["name"] == "Alice"
        assert row["age"] == 30

    def test_fetchone_not_found_returns_none(self, conn):
        row = conn.fetchone("SELECT * FROM users WHERE id = 999")
        assert row is None

    def test_fetchall_returns_list_of_dict(self, conn):
        conn.insert("users", {"name": "A"})
        conn.insert("users", {"name": "B"})
        rows = conn.fetchall("SELECT name FROM users ORDER BY id")
        assert isinstance(rows, list)
        assert len(rows) == 2
        assert all(isinstance(r, dict) for r in rows)

    def test_fetchall_empty(self, conn):
        rows = conn.fetchall("SELECT * FROM users")
        assert rows == []


class TestUpdate:

    def test_update_returns_rowcount(self, conn):
        conn.insert("users", {"name": "Alice", "age": 20})
        cnt = conn.update("users", {"age": 21}, "id = ?", (1,))
        assert cnt == 1
        row = conn.fetchone("SELECT age FROM users WHERE id = 1")
        assert row["age"] == 21

    def test_update_no_match(self, conn):
        cnt = conn.update("users", {"age": 99}, "id = ?", (999,))
        assert cnt == 0


class TestDelete:

    def test_delete_returns_rowcount(self, conn):
        conn.insert("users", {"name": "Alice"})
        cnt = conn.delete("users", "id = ?", (1,))
        assert cnt == 1
        assert conn.fetchone("SELECT * FROM users WHERE id = 1") is None

    def test_delete_no_match(self, conn):
        cnt = conn.delete("users", "id = ?", (999,))
        assert cnt == 0
