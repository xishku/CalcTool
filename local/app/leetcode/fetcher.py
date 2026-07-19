"""
题库获取与题目解析模块 — 通过 REST API 获取题目列表。
"""
import re
import json
import logging
from typing import Optional

from bs4 import BeautifulSoup
from client import LeetCodeClient
from models import Problem, ProblemExample

logger = logging.getLogger(__name__)

# 难度映射：REST API level → 文字
DIFFICULTY_MAP = {1: "Easy", 2: "Medium", 3: "Hard"}

# REST API 端点：一次性返回所有题目
API_PROBLEMS_ALL = "/api/problems/all/"

# GraphQL 查询：题目详情（这个端点可用）
QUERY_PROBLEM_DETAIL = """
query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionId
    questionFrontendId
    title
    titleSlug
    content
    difficulty
    topicTags { name slug translatedName }
    codeSnippets { lang langSlug code }
    sampleTestCase
    exampleTestcases
    mysqlSchemas
    dataSchemas
    hints
    similarQuestions
  }
}
"""


class Fetcher:
    """题库获取与题目解析"""

    def __init__(self, client: LeetCodeClient):
        self.client = client
        self._all_problems: Optional[list] = None  # 缓存全量题目列表

    # ── 题目列表（REST API）──────────────────────────────────────────

    def _load_all_problems(self) -> list:
        """从 REST API 加载全量题目并缓存（一次请求 ~3000+ 题）"""
        if self._all_problems is not None:
            return self._all_problems

        url = self.client.base_url + API_PROBLEMS_ALL
        logger.info(f"正在从 REST API 加载全量题库: {url}")
        resp = self.client.get(url)
        data = resp.json()
        pairs = data.get("stat_status_pairs", [])

        problems = []
        for p in pairs:
            stat = p.get("stat", {})
            diff_level = p.get("difficulty", {}).get("level", 1)
            problems.append({
                "frontendQuestionId": str(stat.get("frontend_question_id", "")),
                "title": stat.get("question__title", ""),
                "titleSlug": stat.get("question__title_slug", ""),
                "difficulty": DIFFICULTY_MAP.get(diff_level, "Easy"),
                "paidOnly": p.get("paid_only", False),
                "questionId": stat.get("question_id", 0),
            })

        self._all_problems = problems
        logger.info(f"已加载 {len(problems)} 道题目")
        return problems

    def get_problem_list(
        self,
        skip: int = 0,
        limit: int = 50,
        difficulty: str = None,
        tags: list = None,
    ) -> dict:
        """获取题目列表（分页 + 难度过滤）"""
        if tags:
            logger.warning("REST API 不支持标签过滤，将返回所有标签的题目")

        all_p = self._load_all_problems()

        # 难度过滤
        if difficulty:
            all_p = [p for p in all_p if p["difficulty"] == difficulty]

        total = len(all_p)
        page = all_p[skip : skip + limit]

        return {
            "questions": page,
            "totalNum": total,
        }

    def search_by_id(self, frontend_id: str) -> Optional[str]:
        """通过题号查找 slug"""
        all_p = self._load_all_problems()
        for p in all_p:
            if p["frontendQuestionId"] == frontend_id:
                slug = p["titleSlug"]
                logger.info(f"题号 {frontend_id} → slug: {slug}")
                return slug
        logger.warning(f"未找到题号 {frontend_id}")
        return None

    # ── 题目详情（GraphQL — 仍可用）─────────────────────────────────

    def get_problem_detail(self, title_slug: str) -> Problem:
        """获取题目详情并解析为 Problem 模型"""
        variables = {"titleSlug": title_slug}
        data = self.client.graphql(QUERY_PROBLEM_DETAIL, variables)
        q = data.get("question")
        if not q:
            raise ValueError(f"未找到题目: {title_slug}")

        content_html = q.get("content", "") or ""

        return Problem(
            question_id=q.get("questionId", ""),
            frontend_id=q.get("questionFrontendId", ""),
            title=q.get("title", ""),
            title_slug=q.get("titleSlug", title_slug),
            difficulty=q.get("difficulty", "Unknown"),
            tags=[t.get("translatedName") or t.get("name", "") for t in (q.get("topicTags") or [])],
            content_html=content_html,
            content_text=self._html_to_text(content_html),
            examples=self._parse_examples(content_html, q.get("exampleTestcases", "")),
            constraints=self._parse_constraints(content_html),
            code_template=self._extract_js_template(q.get("codeSnippets") or []),
            function_signature=self._extract_function_signature(q.get("codeSnippets") or []),
        )

    # ── HTML 解析 ────────────────────────────────────────────────────

    @staticmethod
    def _html_to_text(html: str) -> str:
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")
        for pre in soup.find_all("pre"):
            pre.string = "\n" + pre.get_text() + "\n"
        text = soup.get_text()
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _parse_examples(content_html: str, example_testcases: str) -> list:
        examples = []
        if content_html:
            soup = BeautifulSoup(content_html, "html.parser")
            for pre in soup.find_all("pre"):
                text = pre.get_text().strip()
                if "输入" in text or "输出" in text or "Input" in text:
                    examples.append(Fetcher._parse_single_example(text))

        if not examples and example_testcases:
            lines = example_testcases.strip().split("\n")
            for i in range(0, len(lines), 2):
                inp = lines[i].strip() if i < len(lines) else ""
                out = lines[i + 1].strip() if i + 1 < len(lines) else ""
                examples.append(ProblemExample(input_text=inp, output_text=out))

        if not examples:
            examples.append(ProblemExample(input_text="(见题目描述)", output_text="(见题目描述)"))
        return examples

    @staticmethod
    def _parse_single_example(text: str) -> ProblemExample:
        inp = out = ""
        m = re.search(r"输入[：:]\s*(.+?)(?=输出[：:]|$)", text, re.DOTALL)
        if m: inp = m.group(1).strip()
        m = re.search(r"输出[：:]\s*(.+?)(?=解释[：:]|$)", text, re.DOTALL)
        if m: out = m.group(1).strip()
        m = re.search(r"解释[：:]\s*(.+)", text, re.DOTALL)
        explanation = m.group(1).strip() if m else ""
        if not inp and not out:
            inp = text.strip()
        return ProblemExample(input_text=inp, output_text=out, explanation=explanation)

    @staticmethod
    def _parse_constraints(content_html: str) -> list:
        constraints = []
        if not content_html:
            return constraints
        soup = BeautifulSoup(content_html, "html.parser")
        for li in soup.find_all("li"):
            txt = li.get_text().strip()
            if any(ch in txt for ch in ["<", ">", "=", "10^"]):
                constraints.append(txt)
        if not constraints:
            m = re.search(r"提示[：:]\s*(.+)", Fetcher._html_to_text(content_html))
            if m:
                constraints.append(m.group(1))
        return constraints

    @staticmethod
    def _extract_js_template(snippets: list) -> str:
        for s in snippets:
            if s.get("langSlug") in ("javascript", "typescript"):
                return s.get("code", "")
        for s in snippets:
            if s.get("lang") in ("JavaScript", "TypeScript", "javascript"):
                return s.get("code", "")
        return ""

    @staticmethod
    def _extract_function_signature(snippets: list) -> str:
        template = Fetcher._extract_js_template(snippets)
        if not template:
            return ""
        lines = template.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("//") or line.startswith("/*") or line.startswith("*"):
                continue
            if "function" in line or "=>" in line:
                return line.rstrip(" {")
        return lines[-1].rstrip(" {") if lines else ""
