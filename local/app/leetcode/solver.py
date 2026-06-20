"""
代码生成模块 — 支持两种模式：
  1. 浏览器模式：通过 Playwright 自动化访问 chat.deepseek.com 网页版
  2. API 模式：通过 OpenAI 兼容接口调用 LLM
"""
import logging
import re
import time
from pathlib import Path
from typing import Optional

from config import Config
from models import Problem

logger = logging.getLogger(__name__)

# 生成代码的 System Prompt
SYSTEM_PROMPT = """你是 LeetCode 算法专家。根据题目描述和要求，生成 JavaScript 解法代码。

要求：
1. 只输出可运行的 JavaScript 代码，不要包含任何代码块标记（```javascript 或 ```）
2. 严格遵循给定的函数签名
3. 不要添加额外的 import / require / module.exports
4. 代码前用注释简要说明解题思路和时间复杂度
5. 力求最优解，如果不会做则输出暴力解
6. 不要输出除代码以外的任何文字

输出格式（严格按此格式）：
// 思路：xxx
// 时间复杂度：O(xxx)，空间复杂度：O(xxx)
var functionName = function(params) {
    // 你的代码
};
"""

STATE_DIR = Path(__file__).parent / ".browser_state"


class BrowserSolver:
    """基于 Playwright 浏览器自动化的网页版求解器 — 访问 chat.deepseek.com

    首次使用需要手动登录 DeepSeek：
    - headless: false 模式下会自动弹出浏览器窗口
    - 手动完成登录后，会话状态自动保存到 .browser_state/
    - 后续运行自动加载已保存的登录状态
    """

    def __init__(self, config: Config):
        self.cfg = config
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._logged_in = False
        self._state_file = STATE_DIR / "deepseek_state.json"

    def _ensure_browser(self):
        """延迟启动浏览器，支持 3 种登录来源（优先级递减）：
        1. 预置 deepseek_cookie（config 中配置）
        2. 已保存的 storage_state 文件
        3. 无状态启动 → 交互式登录
        """
        if self._page is not None:
            return

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError(
                "请先安装 Playwright：\n"
                "  pip install playwright\n"
                "  playwright install chromium"
            )

        logger.info("正在启动浏览器...")
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.cfg.llm.headless,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )

        # 加载已保存的会话状态（storage_state 优先级低于显式 cookie）
        storage_state = None
        if self._state_file.exists():
            try:
                storage_state = str(self._state_file)
                logger.info("加载已保存的登录状态...")
            except Exception as e:
                logger.warning(f"加载状态文件失败: {e}")

        self._context = self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
            storage_state=storage_state,
        )

        # 如果配置了 pre-set cookie，注入到浏览器上下文
        if self.cfg.llm.deepseek_cookie:
            self._inject_cookies(self.cfg.llm.deepseek_cookie)
            logger.info("已注入 DeepSeek Cookie")

        self._page = self._context.new_page()
        logger.info("浏览器已启动")

    def _inject_cookies(self, cookie_str: str):
        """将 Cookie 字符串解析并注入到浏览器上下文"""
        cookies = []
        for item in cookie_str.split("; "):
            item = item.strip()
            if "=" not in item:
                continue
            name, _, value = item.partition("=")
            if name and value:
                cookies.append({
                    "name": name,
                    "value": value,
                    "domain": ".deepseek.com",
                    "path": "/",
                    "httpOnly": False,
                    "secure": True,
                    "sameSite": "Lax",
                })
        if cookies:
            self._context.add_cookies(cookies)

    def close(self):
        """关闭浏览器"""
        self._save_state()
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass

        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None

    def solve(self, problem: Problem) -> str:
        """通过网页聊天生成代码"""
        self._ensure_browser()

        # 先确保已登录
        self._ensure_logged_in()

        user_message = build_user_prompt(problem)
        logger.info(f"正在为 {problem.frontend_id}. {problem.title} 生成代码...")

        for attempt in range(self.cfg.llm.retry_count + 1):
            try:
                self._ensure_chat_ready()
                raw = self._do_chat(user_message)
                code = clean_code(raw)
                if code and _validate_signature(code, problem.function_signature):
                    logger.info(f"代码生成成功 ({len(code)} 字符)")
                    return code
                logger.warning(f"代码格式校验不通过，第 {attempt+1} 次重试...")
                self._page.reload()
                time.sleep(3)
            except Exception as e:
                logger.error(f"网页调用失败 (attempt {attempt+1}): {e}")
                if attempt == self.cfg.llm.retry_count:
                    raise RuntimeError(f"代码生成失败，已重试 {self.cfg.llm.retry_count} 次") from e
                time.sleep(3)

        raise RuntimeError("代码生成失败：无法生成符合格式要求的代码")

    # ---- 登录处理 ----

    def _ensure_logged_in(self):
        """确保已登录 DeepSeek，未登录则引导手动登录"""
        if self._logged_in:
            return

        page = self._page
        page.goto(self.cfg.llm.chat_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        # 检查是否被重定向到登录页
        current_url = page.url
        if "/sign_in" in current_url or "/login" in current_url:
            # 用户预置了 Cookie 但无效
            if self.cfg.llm.deepseek_cookie:
                raise RuntimeError(
                    "预置的 DeepSeek Cookie 无效或已过期，仍需登录！\n"
                    "请更新 config.yaml 中的 llm.deepseek_cookie。\n"
                    "获取方式: 浏览器登录 chat.deepseek.com → F12 → Application → Cookies → 复制全部 Cookie"
                )

            if self.cfg.llm.headless:
                self.close()
                raise RuntimeError(
                    "DeepSeek 需要登录！\n"
                    "方式 1: 在 config.yaml 中设置 llm.deepseek_cookie（推荐）\n"
                    "方式 2: 设置 llm.headless: false，在弹出的浏览器中手动登录"
                )

            # 非无头模式：交互式登录
            self._interactive_login(page)
            return

            # 非无头模式：交互式登录 — 可靠且简单
            self._interactive_login(page)
            return

        # 已在聊天页，说明已登录
        self._logged_in = True
        logger.info("DeepSeek 已登录 ✓")

    def _interactive_login(self, page):
        """交互式登录：用户登录后在终端按 Enter 确认"""
        page.bring_to_front()

        print("\n" + "=" * 60)
        print("  请在浏览器窗口中完成 DeepSeek 登录")
        print("  支持：手机号、邮箱、微信扫码等方式")
        print("=" * 60)

        # 等待用户在终端按 Enter 确认登录完成
        print("\n  >>> 登录完成后，回到此处按 Enter 继续 <<<\n")
        input()

        # 等待页面稳定
        time.sleep(3)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

        # 确认登录成功
        url = page.url
        if "/sign_in" in url or "/login" in url:
            logger.warning(f"仍在登录页 ({url})，再试一次...")
            print("\n  似乎仍在登录页，请确认已完成登录后按 Enter...")
            input()
            time.sleep(3)
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            url = page.url
            if "/sign_in" in url or "/login" in url:
                raise RuntimeError("登录未完成，仍在登录页面。请重试。")

        logger.info(f"登录确认完成，当前页: {url}")
        self._save_state()
        self._logged_in = True

    def _save_state(self):
        """立即保存浏览器登录状态到文件"""
        try:
            if self._context:
                STATE_DIR.mkdir(parents=True, exist_ok=True)
                self._context.storage_state(path=str(self._state_file))
                logger.info(f"登录状态已保存到 {self._state_file}")
                self._logged_in = True
        except Exception as e:
            logger.warning(f"保存状态失败: {e}")

    # ---- 聊天交互 ----

    def _ensure_chat_ready(self):
        """确保聊天页面已加载并可以输入"""
        page = self._page

        # 确保在聊天页
        chat_url = self.cfg.llm.chat_url.rstrip("/")
        if not page.url.startswith(chat_url):
            page.goto(self.cfg.llm.chat_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

        # 等待页面加载：networkidle 确保 JS 渲染完成
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            logger.warning("页面未在 15s 内完成加载，继续尝试...")

        # 诊断：打印页面信息
        logger.info(f"当前 URL: {page.url}")
        logger.info(f"页面标题: {page.title()}")
        self._diagnose_page()

        # 最大等待 30 秒让输入框出现
        deadline = time.time() + 30
        while time.time() < deadline:
            textarea = self._find_textarea()
            if textarea:
                logger.info("聊天输入框就绪 ✓")
                return
            logger.info(f"等待输入框出现... (已等 {int(time.time() - (deadline - 30))}s)")
            time.sleep(3)

        # 失败时再次诊断
        logger.error("找不到输入框，页面诊断信息：")
        self._diagnose_page()
        raise RuntimeError("找不到 DeepSeek 聊天输入框，请确认页面结构和登录状态")

    def _diagnose_page(self):
        """诊断页面当前状态"""
        page = self._page
        try:
            info = page.evaluate("""() => {
                const result = {
                    url: location.href,
                    readyState: document.readyState,
                    textareas: document.querySelectorAll('textarea').length,
                    contenteditables: document.querySelectorAll('[contenteditable="true"]').length,
                    textboxes: document.querySelectorAll('[role="textbox"]').length,
                    inputs: document.querySelectorAll('input').length,
                    visibleElements: []
                };
                // 检查常见输入元素
                const candidates = document.querySelectorAll(
                    'textarea, [contenteditable="true"], [role="textbox"], ' +
                    'input[type="text"], input:not([type])'
                );
                candidates.forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        result.visibleElements.push({
                            tag: el.tagName,
                            id: el.id,
                            class: el.className?.substring(0, 100),
                            placeholder: el.placeholder || el.getAttribute('aria-label') || '',
                            role: el.getAttribute('role'),
                            rect: {w: rect.width, h: rect.height, x: rect.x, y: rect.y}
                        });
                    }
                });
                // 检查是否有登录相关元素
                result.hasSignIn = !!document.querySelector('[class*="sign"], [class*="login"], [class*="Sign"], [class*="Login"]');
                return result;
            }""")
            logger.info(f"页面诊断: url={info.get('url')}")
            logger.info(f"  readyState={info.get('readyState')}")
            logger.info(f"  textareas={info.get('textareas')}, contenteditables={info.get('contenteditables')}")
            logger.info(f"  textboxes={info.get('textboxes')}, inputs={info.get('inputs')}")
            logger.info(f"  hasSignIn={info.get('hasSignIn')}")
            visible = info.get('visibleElements', [])
            if visible:
                for v in visible:
                    logger.info(f"  可见元素: <{v['tag']}> id={v['id']} class={v['class'][:60]} "
                                f"placeholder={v['placeholder'][:30]} role={v['role']}")
            else:
                logger.warning("  ⚠️ 未找到任何可见的输入元素！页面可能未加载完成或需要额外操作。")
        except Exception as e:
            logger.error(f"页面诊断失败: {e}")

    def _find_textarea(self):
        """尝试多种选择器找到输入框"""
        page = self._page
        # 按优先级尝试
        for selector in [
            "textarea",
            '[contenteditable="true"]',
            '[role="textbox"]',
            "#chat-input",
            '[class*="chat"] textarea',
            '[class*="chat"] [contenteditable]',
            ".ds-markdown ~ textarea",
            "form textarea",
        ]:
            try:
                el = page.locator(selector).first
                if el.count() > 0 and el.is_visible():
                    logger.info(f"输入框选择器匹配: {selector}")
                    return el
            except Exception:
                continue
        return None

    def _do_chat(self, message: str) -> str:
        """发送消息并等待 AI 回复"""
        page = self._page

        textarea = self._find_textarea()
        if textarea is None:
            raise RuntimeError("无法找到聊天输入框")

        # 点击获取焦点 → 清空 → 填入消息
        textarea.click()
        time.sleep(0.3)
        textarea.fill("")
        time.sleep(0.2)
        textarea.fill(message)
        time.sleep(0.3)

        # Enter 发送
        page.keyboard.press("Enter")
        logger.info("消息已发送，等待 AI 回复...")
        time.sleep(2)

        return self._wait_for_response()

    def _wait_for_response(self) -> str:
        """轮询等待 AI 回复完成"""
        page = self._page
        start = time.time()
        timeout = self.cfg.llm.timeout_seconds
        poll = self.cfg.llm.poll_interval

        prev_text = ""
        stable_count = 0

        while time.time() - start < timeout:
            # 检查停止按钮是否仍在（= 正在生成）
            try:
                stop_btn = page.locator("button:has-text('停止'), [class*='stop'], [class*='Stop']")
                still_generating = stop_btn.count() > 0 and stop_btn.first.is_visible()
            except Exception:
                still_generating = False

            try:
                current_text = self._extract_last_response()
            except Exception:
                current_text = ""

            if current_text and not still_generating:
                if current_text == prev_text:
                    stable_count += 1
                    if stable_count >= 3:
                        logger.info(f"AI 回复完成 ({len(current_text)} 字符)")
                        return current_text
                else:
                    stable_count = 0
                    prev_text = current_text
            else:
                stable_count = 0

            time.sleep(poll)

        raise TimeoutError(f"等待 AI 回复超时 ({timeout}s)")

    def _extract_last_response(self) -> str:
        """提取最后一条 AI 回复"""
        page = self._page

        # DeepSeek 页面常见选择器
        for selector in [
            ".ds-markdown",
            '[class*="markdown"]',
            '[class*="message"]',
            '[class*="Message"]',
        ]:
            try:
                elems = page.locator(selector)
                n = elems.count()
                if n > 0:
                    text = elems.nth(n - 1).inner_text(timeout=2000)
                    if text and len(text) > 20:
                        return text.strip()
            except Exception:
                continue

        # 备选：取 body 中最后的一大段
        try:
            body = page.locator("body").inner_text(timeout=2000)
            parts = [p.strip() for p in body.split("\n\n") if len(p.strip()) > 50]
            if parts:
                return parts[-1]
        except Exception:
            pass

        return ""


class ApiSolver:
    """基于 OpenAI 兼容 API 的求解器"""

    def __init__(self, config: Config):
        from openai import OpenAI

        self.cfg = config
        api_key = config.llm.api_key
        if not api_key:
            raise ValueError("LLM API Key 未设置！请在 config.yaml 中配置或设置环境变量 LLM_API_KEY")

        self.client = OpenAI(api_key=api_key, base_url=config.llm.base_url)

    def solve(self, problem: Problem) -> str:
        user_message = build_user_prompt(problem)
        logger.info(f"正在为 {problem.frontend_id}. {problem.title} 生成代码...")

        for attempt in range(self.cfg.llm.retry_count + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=self.cfg.llm.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=self.cfg.llm.temperature,
                    max_tokens=self.cfg.llm.max_tokens,
                )
                raw = resp.choices[0].message.content or ""
                code = clean_code(raw)
                if code and _validate_signature(code, problem.function_signature):
                    logger.info(f"代码生成成功 ({len(code)} 字符)")
                    return code
                logger.warning(f"代码格式校验不通过，第 {attempt+1} 次重试...")
            except Exception as e:
                logger.error(f"API 调用失败 (attempt {attempt+1}): {e}")
                if attempt == self.cfg.llm.retry_count:
                    raise RuntimeError(f"代码生成失败，已重试 {self.cfg.llm.retry_count} 次") from e

        raise RuntimeError("代码生成失败：无法生成符合格式要求的代码")


# ---- 工具函数 ----

def build_user_prompt(problem: Problem) -> str:
    """构造用户 Prompt"""
    parts = [
        f"## 题目 [{problem.frontend_id}] {problem.title}",
        f"难度: {problem.difficulty}",
        f"标签: {', '.join(problem.tags)}",
        "",
        "## 题目描述",
        problem.content_text,
        "",
        "## 函数签名 (必须以此签名输出代码)",
        f"```\n{problem.function_signature}\n```",
        "",
        "## 输入输出示例",
    ]
    for i, ex in enumerate(problem.examples[:3], 1):
        parts.append(f"示例 {i}:")
        parts.append(f"  输入: {ex.input_text}")
        parts.append(f"  输出: {ex.output_text}")
        if ex.explanation:
            parts.append(f"  解释: {ex.explanation}")

    if problem.constraints:
        parts.append("")
        parts.append("## 约束条件")
        for c in problem.constraints:
            parts.append(f"  - {c}")

    parts.append("")
    parts.append("请直接输出 JavaScript 代码，不要包含代码块标记。")
    return "\n".join(parts)


def clean_code(raw: str) -> str:
    """清理代码：移除 Markdown 代码块标记和多余内容"""
    code = raw
    code = re.sub(r"^```(?:javascript|js|typescript)?\s*\n?", "", code, flags=re.MULTILINE)
    code = re.sub(r"\n?```\s*$", "", code)
    code = code.strip()

    lines = code.split("\n")
    start_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("//") and not stripped.startswith("/*"):
            if any(stripped.startswith(kw) for kw in ["var ", "const ", "let ", "function "]):
                start_idx = i
                break

    end_idx = len(lines) - 1
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip() in ("}", "};"):
            end_idx = i
            break

    code = "\n".join(lines[start_idx:end_idx + 1])
    return code.strip()


def _validate_signature(code: str, expected_signature: str) -> bool:
    """校验代码是否包含要求的函数签名"""
    if not expected_signature:
        return bool(code)
    sig_name = expected_signature.split("(")[0].strip()
    sig_name = sig_name.replace("var ", "").replace("const ", "").replace("let ", "").strip()
    sig_name = sig_name.replace(" = function", "").strip()
    return sig_name in code if sig_name else bool(len(code) > 20)


def create_solver(config: Config):
    """工厂方法：根据配置创建对应的 Solver"""
    mode = config.llm.mode
    if mode == "browser":
        logger.info("使用浏览器模式（Playwright → chat.deepseek.com）")
        return BrowserSolver(config)
    elif mode == "api":
        logger.info("使用 API 模式")
        return ApiSolver(config)
    else:
        raise ValueError(f"不支持的 llm.mode: {mode}，可选值: browser / api")
