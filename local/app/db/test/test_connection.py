"""测试 Connection 生命周期：打开、关闭、上下文管理器"""

import os
import sys
import tempfile

import pytest

# 确保 src 路径可导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dbutil import Connection, DBError
from dbutil.exceptions import DBConnectionError


class TestConnectionLifecycle:

    def test_open_creates_parent_dirs(self):
        """打开数据库时自动创建父目录"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "sub", "test.db")
            conn = Connection(db_path)
            conn.open()
            assert os.path.isfile(db_path)
            conn.close()

    def test_context_manager(self):
        """with 语句自动打开/关闭"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "ctx.db")
            with Connection(db_path) as conn:
                assert conn.raw is not None
            # 离开 with 后 raw 属性应触发异常
            with pytest.raises(DBConnectionError):
                _ = conn.raw

    def test_close_twice_is_safe(self):
        """重复 close 安全无异常"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "safe.db")
            conn = Connection(db_path)
            conn.open()
            conn.close()
            conn.close()  # 不抛异常

    def test_path_property(self):
        """path 属性返回绝对路径"""
        conn = Connection("relative.db")
        assert os.path.isabs(conn.path)
        assert conn.path.endswith("relative.db")
