"""测试 DBManager 配置加载和多实例管理"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dbutil import DB, DBManager


@pytest.fixture(autouse=True)
def reset_manager():
    """每个测试前后重置单例"""
    DBManager.reset()
    DB.reset()
    yield
    DBManager.reset()
    DB.reset()


@pytest.fixture
def config_file():
    """创建临时 YAML 配置文件"""
    import yaml

    with tempfile.TemporaryDirectory() as tmp:
        config_path = os.path.join(tmp, "db_config.yaml")
        data = {
            "databases": {
                "app1": {
                    "path": "data/app1.db",
                    "timeout": 5,
                },
                "app2": {
                    "path": "data/app2.db",
                },
            }
        }
        with open(config_path, "w") as f:
            yaml.dump(data, f)

        # 切换到 tmp 目录确保相对路径正确
        old_cwd = os.getcwd()
        os.chdir(tmp)
        try:
            yield config_path
        finally:
            os.chdir(old_cwd)


class TestDBManager:

    def test_load_config(self, config_file):
        manager = DBManager.load(config_file)
        assert "app1" in manager.list_names()
        assert "app2" in manager.list_names()

    def test_get_connection(self, config_file):
        manager = DBManager.load(config_file)
        conn = manager.get("app1")
        assert isinstance(conn.path, str)
        assert conn.path.endswith("app1.db")

    def test_get_unknown_name_raises(self, config_file):
        manager = DBManager.load(config_file)
        with pytest.raises(KeyError):
            manager.get("nonexistent")

    def test_singleton_behavior(self, config_file):
        m1 = DBManager.load(config_file)
        m2 = DBManager.load(config_file)
        assert m1 is m2


class TestDBEntryPoint:

    def test_db_get(self, config_file):
        conn = DB.get("app1", config_path=config_file)
        assert "app1.db" in conn.path

    def test_db_list_databases(self, config_file):
        names = DB.list_databases(config_path=config_file)
        assert "app1" in names
        assert "app2" in names

    def test_db_open_direct(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "direct.db")
            with DB.open(db_path) as conn:
                conn.execute("CREATE TABLE t (x INTEGER)")
                conn.insert("t", {"x": 42})
                assert conn.fetchone("SELECT * FROM t")["x"] == 42
