"""
HTTP 客户端 — 统一请求封装，管理 Cookie / CSRF / 重试 / 限流。
"""
import re
import time
import logging
import requests
from typing import Optional
from config import Config

logger = logging.getLogger(__name__)


class LeetCodeClient:
    """LeetCode HTTP 客户端"""

    def __init__(self, config: Config):
        self.cfg = config
        self.base_url = config.leetcode.base_url
        self.graphql_url = config.leetcode.graphql_url
        self.session = requests.Session()
        self._last_request_time = 0
        self._setup_session()

    def _setup_session(self):
        """初始化 Session — 设置 Cookie、CSRF Token、User-Agent"""
        cookie_str = self.cfg.auth.cookie
        if cookie_str:
            # 用 session.cookies 逐条设置（比 raw Cookie header 更可靠，避免格式问题）
            for item in cookie_str.split(";"):
                item = item.strip()
                if "=" in item:
                    k, v = item.split("=", 1)
                    self.session.cookies.set(k.strip(), v.strip(), domain=".leetcode.cn")
            logger.info(f"已设置 {len(self.session.cookies)} 条 Cookie")

        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/125.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": self.base_url,
            "Referer": self.base_url + "/",
            "x-requested-with": "XMLHttpRequest",
        })
        # 设置 CSRF Token
        csrf = self._extract_csrf()
        if csrf:
            self.session.headers["x-csrftoken"] = csrf
            logger.info("CSRF Token OK")
        else:
            logger.warning("未提取到 CSRF Token，提交可能失败")

    @staticmethod
    def _parse_cookie(cookie_str: str) -> dict:
        """解析 Cookie 字符串为字典（备用）"""
        cookies = {}
        for item in cookie_str.split(";"):
            item = item.strip()
            if "=" in item:
                k, v = item.split("=", 1)
                cookies[k.strip()] = v.strip()
        return cookies

    def _extract_csrf(self) -> Optional[str]:
        """从 Cookie 字符串中提取 csrftoken"""
        if self.cfg.auth.cookie:
            m = re.search(r"csrftoken=([^;]+)", self.cfg.auth.cookie)
            if m:
                return m.group(1)
        return None

    def _rate_limit(self):
        """请求限流 — 确保两次请求间隔不小于配置值"""
        elapsed = time.monotonic() - self._last_request_time
        min_interval = self.cfg.request.interval_seconds
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_time = time.monotonic()

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """带重试的请求封装"""
        timeout = kwargs.pop("timeout", self.cfg.request.timeout_seconds)
        max_retries = self.cfg.request.max_retries
        backoff = self.cfg.request.retry_backoff

        self._rate_limit()

        for attempt in range(max_retries + 1):
            try:
                resp = self.session.request(method, url, timeout=timeout, **kwargs)
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 30))
                    logger.warning(f"限流 429，等待 {retry_after}s...")
                    time.sleep(retry_after)
                    continue
                if resp.status_code == 401:
                    logger.error("认证失败 (401)，请检查 Cookie 是否有效")
                    raise PermissionError("Cookie 已过期，请重新提供")
                resp.raise_for_status()
                return resp
            except requests.Timeout:
                if attempt < max_retries:
                    wait = backoff ** attempt
                    logger.warning(f"请求超时，第 {attempt+1}/{max_retries} 次重试，等待 {wait}s...")
                    time.sleep(wait)
                else:
                    raise
            except requests.HTTPError as e:
                # 打印响应体帮助排查
                try:
                    body = e.response.text[:800] if e.response is not None else ""
                    status = e.response.status_code if e.response is not None else "?"
                    req_headers = dict(e.response.request.headers) if e.response is not None and e.response.request else {}
                except Exception:
                    body = ""
                    status = "?"
                    req_headers = {}
                if attempt < max_retries:
                    wait = backoff ** attempt
                    logger.warning(
                        f"请求失败: HTTP {status} for {method} {url}，"
                        f"第 {attempt+1}/{max_retries} 次重试，等待 {wait}s...\n"
                        f"  请求头: {req_headers}\n"
                        f"  响应: {body}"
                    )
                    time.sleep(wait)
                else:
                    logger.error(f"请求最终失败 [HTTP {status}]，响应: {body}")
                    raise
            except requests.RequestException as e:
                if attempt < max_retries:
                    wait = backoff ** attempt
                    logger.warning(f"请求失败: {e}，第 {attempt+1}/{max_retries} 次重试，等待 {wait}s...")
                    time.sleep(wait)
                else:
                    raise
        # 不会到达此处，但让类型检查器满意
        raise RuntimeError("请求失败，已达最大重试次数")

    def get(self, url: str, **kwargs) -> requests.Response:
        return self._request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        return self._request("POST", url, **kwargs)

    def graphql(self, query: str, variables: dict = None, operation_name: str = None) -> dict:
        """GraphQL 查询"""
        payload = {"query": query, "variables": variables or {}}
        if operation_name:
            payload["operationName"] = operation_name
        resp = self.post(self.graphql_url, json=payload)
        data = resp.json()
        if "errors" in data:
            logger.error(f"GraphQL 错误: {data['errors']}")
            raise RuntimeError(f"GraphQL 查询失败: {data['errors']}")
        return data.get("data", {})

    def verify_auth(self) -> bool:
        """验证认证状态 — 访问首页检查是否重定向到登录页"""
        logger.info("正在验证登录状态...")
        try:
            resp = self.get(self.base_url, allow_redirects=False, timeout=self.cfg.request.timeout_seconds)
            if resp.status_code in (301, 302):
                location = resp.headers.get("Location", "")
                if "login" in location.lower():
                    logger.error(f"Cookie 无效，被重定向到登录页: {location}")
                    return False
            # 检查页面内容是否包含登录入口
            text = resp.text[:2000].lower()
            if "accounts/login" in text and "isSignedIn" not in text:
                logger.warning("页面需要登录，可能 Cookie 已过期")
                return False

            # 尝试 GraphQL 查询确认
            try:
                query = """
                query globalData {
                  userStatus {
                    username
                    isSignedIn
                  }
                }
                """
                data = self.graphql(query)
                user_status = data.get("userStatus", {})
                if user_status.get("isSignedIn"):
                    username = user_status.get("username", "unknown")
                    logger.info(f"认证成功，用户: {username}")
                    return True
            except Exception as e:
                logger.warning(f"GraphQL 验证跳过（非致命）: {e}")

            # GraphQL 失败但页面访问成功 → 可能仍然可用
            if resp.status_code == 200:
                logger.info("首页访问正常，假定认证有效")
                return True
            logger.warning("认证验证未通过")
            return False
        except Exception as e:
            logger.error(f"认证验证失败: {e}")
            return False
