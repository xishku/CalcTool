"""
题库获取与题目解析模块。
"""
import re
import json
import logging
from typing import Optional
from bs4 import BeautifulSoup

from client import LeetCodeClient
from models import Problem, ProblemExample

logger = logging.getLogger(__name__)


# GraphQL 查询：题目列表
QUERY_PROBLEM_LIST = """
query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
  problemsetQuestionList: questionList(
    categorySlug: $categorySlug
    limit: $limit
    skip: $skip
    filters: $filters
  ) {
    total: totalNum
    questions: data {
      frontendQuestionId
      title
      titleSlug
      difficulty
      topicTags { name slug translatedName }
    }
  }
}
"""

# GraphQL 查询：题目详情
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

    def get_problem_list(
        self,
        skip: int = 0,
        limit: int = 50,
        difficulty: str = None,
        tags: list = None,
    ) -> dict:
        """获取题目列表"""
        filters = {}
        if difficulty:
            filters["difficulty"] = difficulty.upper()
        if tags:
            filters["tags"] = tags

        variables = {
            "categorySlug": "",
            "skip": skip,
            "limit": limit,
            "filters": filters if filters else {},
        }
        data = self.client.graphql(QUERY_PROBLEM_LIST, variables)
        return data.get("problemsetQuestionList", {})

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

    @staticmethod
    def _html_to_text(html: str) -> str:
        """HTML 转纯文本"""
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")
        # 将 <pre> 内容保留换行
        for pre in soup.find_all("pre"):
            pre.string = "\n" + pre.get_text() + "\n"
        text = soup.get_text()
        # 压缩多余空行
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _parse_examples(content_html: str, example_testcases: str) -> list:
        """解析输入/输出示例"""
        examples = []
        # 方法1: 解析 HTML 中的 <pre> 块获取示例
        if content_html:
            soup = BeautifulSoup(content_html, "html.parser")
            pres = soup.find_all("pre")
            for pre in pres:
                text = pre.get_text().strip()
                if "输入" in text or "输出" in text or "Input" in text:
                    examples.append(Fetcher._parse_single_example(text))

        # 方法2: 使用 GraphQL 返回的 exampleTestcases
        if not examples and example_testcases:
            lines = example_testcases.strip().split("\n")
            # 简单处理：每两行一组 input/output
            for i in range(0, len(lines), 2):
                inp = lines[i].strip() if i < len(lines) else ""
                out = lines[i + 1].strip() if i + 1 < len(lines) else ""
                examples.append(ProblemExample(input_text=inp, output_text=out))

        if not examples:
            examples.append(ProblemExample(input_text="(见题目描述)", output_text="(见题目描述)"))

        return examples

    @staticmethod
    def _parse_single_example(text: str) -> ProblemExample:
        """从示例文本中提取 input/output"""
        input_text = ""
        output_text = ""
        explanation = ""

        # 匹配 "输入：" / "输出：" / "解释："
        input_m = re.search(r"输入[：:]\s*(.+?)(?=输出[：:]|$)", text, re.DOTALL)
        output_m = re.search(r"输出[：:]\s*(.+?)(?=解释[：:]|$)", text, re.DOTALL)
        explain_m = re.search(r"解释[：:]\s*(.+)", text, re.DOTALL)

        if input_m:
            input_text = input_m.group(1).strip()
        if output_m:
            output_text = output_m.group(1).strip()
        if explain_m:
            explanation = explain_m.group(1).strip()

        if not input_text and not output_text:
            input_text = text.strip()

        return ProblemExample(input_text=input_text, output_text=output_text, explanation=explanation)

    @staticmethod
    def _parse_constraints(content_html: str) -> list:
        """解析约束条件"""
        constraints = []
        if not content_html:
            return constraints
        soup = BeautifulSoup(content_html, "html.parser")
        # 查找约束列表（通常以 <li> 或 <code> 形式）
        for li in soup.find_all("li"):
            txt = li.get_text().strip()
            # 简单的约束检测：包含 <、>、<=、>=、== 等
            if any(ch in txt for ch in ["<", ">", "=", "10^"]):
                constraints.append(txt)
        if not constraints:
            # 尝试匹配 "提示：" 后的内容
            hint_m = re.search(r"提示[：:]\s*(.+)", Fetcher._html_to_text(content_html))
            if hint_m:
                constraints.append(hint_m.group(1))
        return constraints

    @staticmethod
    def _extract_js_template(snippets: list) -> str:
        """提取 JavaScript 代码模板"""
        for s in snippets:
            if s.get("langSlug") in ("javascript", "typescript"):
                return s.get("code", "")
        # fallback
        for s in snippets:
            if s.get("lang") in ("JavaScript", "TypeScript", "javascript"):
                return s.get("code", "")
        return ""

    @staticmethod
    def _extract_function_signature(snippets: list) -> str:
        """提取 JavaScript 函数签名"""
        template = Fetcher._extract_js_template(snippets)
        if not template:
            return ""
        # 提取 var/const/let functionName = function(...) 或 function name(...)
        lines = template.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("//") or line.startswith("/*") or line.startswith("*"):
                continue
            if "function" in line or "=>" in line:
                return line.rstrip(" {")
        return lines[-1].rstrip(" {") if lines else ""
