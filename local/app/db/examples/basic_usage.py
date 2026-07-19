"""快速上手指南 —— 演示 dbutil 的核心用法"""

import os
import sys
import tempfile

# 将 src 路径加入 sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dbutil import DB


def demo_basic_crud():
    """演示基础 CRUD 操作"""
    print("=" * 50)
    print("  1. 基础 CRUD")
    print("=" * 50)

    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "demo.db")

        with DB.open(db_path) as db:
            # 建表
            db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER)")

            # 插入
            uid = db.insert("users", {"name": "Alice", "age": 30})
            print(f"  insert → lastrowid = {uid}")

            # 批量插入
            db.insert_many("users", ["name", "age"], [["Bob", 25], ["Charlie", 35]])

            # 查询
            alice = db.fetchone("SELECT * FROM users WHERE name = ?", ("Alice",))
            print(f"  fetchone → {alice}")

            all_users = db.fetchall("SELECT name, age FROM users ORDER BY id")
            print(f"  fetchall → {all_users}")

            # 更新
            cnt = db.update("users", {"age": 31}, "name = ?", ("Alice",))
            print(f"  update → {cnt} row(s), new age = {db.fetchone('SELECT age FROM users WHERE name=?', ('Alice',))['age']}")

            # 删除
            cnt = db.delete("users", "name = ?", ("Charlie",))
            print(f"  delete → {cnt} row(s)")
            print(f"  remaining → {len(db.fetchall('SELECT * FROM users'))} users")


def demo_transaction():
    """演示事务提交与回滚"""
    print("\n" + "=" * 50)
    print("  2. 事务支持")
    print("=" * 50)

    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "txn.db")

        with DB.open(db_path) as db:
            db.execute("CREATE TABLE accounts (id INTEGER PRIMARY KEY, balance REAL)")
            db.insert("accounts", {"balance": 1000.0})

            # 成功事务
            with db.transaction():
                db.insert("accounts", {"balance": 200.0})
                db.insert("accounts", {"balance": 300.0})
            print(f"  事务提交后: {len(db.fetchall('SELECT * FROM accounts'))} 行")

            # 回滚事务
            try:
                with db.transaction():
                    db.insert("accounts", {"balance": 999.0})
                    raise ValueError("模拟错误")
            except ValueError:
                pass
            print(f"  事务回滚后: {len(db.fetchall('SELECT * FROM accounts'))} 行 (999未被写入)")


def demo_export():
    """演示导出功能"""
    print("\n" + "=" * 50)
    print("  3. 导出工具")
    print("=" * 50)

    rows = [
        {"id": 1, "name": "Alice", "score": 95.5},
        {"id": 2, "name": "Bob", "score": 87.0},
    ]

    with tempfile.TemporaryDirectory() as tmp:
        csv_path = os.path.join(tmp, "users.csv")
        json_path = os.path.join(tmp, "users.json")

        DB.export_csv(rows, csv_path)
        print(f"  CSV → {csv_path}")

        DB.export_json(rows, json_path)
        print(f"  JSON → {json_path}")


if __name__ == "__main__":
    demo_basic_crud()
    demo_transaction()
    demo_export()
    print("\nAll examples completed successfully!")
