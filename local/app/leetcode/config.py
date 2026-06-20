"""
配置管理模块 — 读取 config.yaml，支持环境变量覆盖。
"""
import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class LeetCodeConfig:
    base_url: str = "https://leetcode.cn"
    graphql_url: str = "https://leetcode.cn/graphql/"


@dataclass
class AuthConfig:
    cookie: str = ""


@dataclass
class RequestConfig:
    timeout_seconds: int = 30
    interval_seconds: int = 3
    max_retries: int = 3
    retry_backoff: int = 2


@dataclass
class LLMConfig:
    mode: str = "browser"              # "browser" or "api"
    # --- 浏览器模式 ---
    chat_url: str = "https://chat.deepseek.com/"
    headless: bool = True
    deepseek_cookie: str = ""         # 预置 DeepSeek Cookie，无需手动登录
    timeout_seconds: int = 120
    poll_interval: int = 2
    retry_count: int = 2
    # --- API 模式 ---
    provider: str = "openai"
    model: str = "deepseek-chat"
    api_key: str = ""
    base_url: str = "https://api.deepseek.com/v1"
    temperature: float = 0.1
    max_tokens: int = 4096


@dataclass
class BatchConfig:
    difficulty_filter: list = field(default_factory=list)
    tag_filter: list = field(default_factory=list)
    max_problems: int = 10
    start_from_id: int = 1


@dataclass
class OutputConfig:
    format: str = "csv"
    directory: str = "./output"


@dataclass
class Config:
    leetcode: LeetCodeConfig = field(default_factory=LeetCodeConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    request: RequestConfig = field(default_factory=RequestConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    batch: BatchConfig = field(default_factory=BatchConfig)
    output: OutputConfig = field(default_factory=OutputConfig)


def load_config(config_path: str = None) -> Config:
    """加载配置文件，优先 config.local.yaml > config.yaml"""
    base_dir = Path(__file__).parent

    if config_path:
        path = Path(config_path)
    else:
        local = base_dir / "config.local.yaml"
        default = base_dir / "config.yaml"
        path = local if local.exists() else default

    if not path.exists():
        print("[WARN] 未找到配置文件，使用默认值。请创建 config.local.yaml 并填入 Cookie。")
        return _apply_env_overrides(Config())

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    cfg = Config(
        leetcode=LeetCodeConfig(**raw.get("leetcode", {})),
        auth=AuthConfig(**raw.get("auth", {})),
        request=RequestConfig(**raw.get("request", {})),
        llm=LLMConfig(**raw.get("llm", {})),
        batch=BatchConfig(**raw.get("batch", {})),
        output=OutputConfig(**raw.get("output", {})),
    )
    return _apply_env_overrides(cfg)


def _apply_env_overrides(cfg: Config) -> Config:
    """环境变量覆盖配置值"""
    if os.getenv("LEETCODE_COOKIE"):
        cfg.auth.cookie = os.getenv("LEETCODE_COOKIE")
    if os.getenv("DEEPSEEK_COOKIE"):
        cfg.llm.deepseek_cookie = os.getenv("DEEPSEEK_COOKIE")
    if os.getenv("LLM_API_KEY"):
        cfg.llm.api_key = os.getenv("LLM_API_KEY")
    if os.getenv("LLM_MODEL"):
        cfg.llm.model = os.getenv("LLM_MODEL")
    if os.getenv("LLM_BASE_URL"):
        cfg.llm.base_url = os.getenv("LLM_BASE_URL")
    return cfg
