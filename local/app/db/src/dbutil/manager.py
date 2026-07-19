"""DBManager —— 基于 YAML 配置的多数据库实例管理"""

import logging
import os
from typing import Any

from .connection import Connection

logger = logging.getLogger(__name__)


class DBManager:
    """数据库管理器（单例）。

    通过 ``db_config.yaml`` 集中管理所有子模块的数据库路径与参数，
    提供按名称获取连接的能力。

    用法::

        manager = DBManager.load("db_config.yaml")
        with manager.get("leetcode") as conn:
            rows = conn.fetchall("SELECT * FROM submissions")
    """

    _instance: "DBManager | None" = None

    def __init__(self) -> None:
        self._databases: dict[str, dict] = {}
        self._config_dir: str = ""

    # ── 单例 ─────────────────────────────────────────────

    @classmethod
    def load(cls, config_path: str = "db_config.yaml") -> "DBManager":
        """加载配置文件（已加载则复用）。

        Args:
            config_path: YAML 配置文件路径

        Returns:
            DBManager 单例
        """
        if cls._instance is not None:
            return cls._instance

        manager = cls()
        manager._load_config(config_path)
        cls._instance = manager
        return manager

    @classmethod
    def reset(cls) -> None:
        """重置单例（主要用于测试）"""
        cls._instance = None

    # ── 公共 API ─────────────────────────────────────────

    def get(self, name: str) -> Connection:
        """按配置名称获取数据库连接。

        Args:
            name: 数据库配置名称（如 "leetcode", "stocks"）

        Returns:
            Connection 实例（未打开，需要 open() 或 with 语句）

        Raises:
            KeyError: 配置中找不到该名称
        """
        if name not in self._databases:
            raise KeyError(f"数据库 '{name}' 未在配置中找到，可用: {list(self._databases.keys())}")
        cfg = self._databases[name]
        return Connection(
            db_path=os.path.join(self._config_dir, cfg["path"])
            if not os.path.isabs(cfg["path"])
            else cfg["path"],
            timeout=cfg.get("timeout", 5),
            migrations=cfg.get("migrations"),
        )

    def list_names(self) -> list[str]:
        """列出所有已配置的数据库名称"""
        return list(self._databases.keys())

    # ── 内部方法 ─────────────────────────────────────────

    def _load_config(self, config_path: str) -> None:
        import yaml

        if not os.path.isfile(config_path):
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        self._config_dir = os.path.dirname(os.path.abspath(config_path))

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or "databases" not in data:
            raise ValueError("配置文件格式错误：缺少 'databases' 根节点")

        self._databases = data["databases"]
        logger.info("已加载 %d 个数据库配置", len(self._databases))
