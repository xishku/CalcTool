"""
数据模型 — Problem 和 SubmissionResult 定义。
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ProblemExample:
    input_text: str
    output_text: str
    explanation: str = ""


@dataclass
class Problem:
    """题目完整信息"""
    question_id: str              # GraphQL 内部 ID
    frontend_id: str              # 显示题号，如 "1"
    title: str                    # 标题，如 "Two Sum"
    title_slug: str               # URL slug，如 "two-sum"
    difficulty: str               # Easy / Medium / Hard
    tags: list = field(default_factory=list)           # ["Array", "Hash Table"]
    content_html: str = ""        # 原始 HTML/Markdown 内容
    content_text: str = ""        # 纯文本内容
    examples: list = field(default_factory=list)       # [ProblemExample, ...]
    constraints: list = field(default_factory=list)    # 约束条件文本列表
    code_template: str = ""       # JavaScript 默认代码模板
    function_signature: str = ""  # 提取的函数签名

    def to_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "frontend_id": self.frontend_id,
            "title": self.title,
            "title_slug": self.title_slug,
            "difficulty": self.difficulty,
            "tags": self.tags,
            "content_text": self.content_text[:500],
            "examples": [{"input": e.input_text, "output": e.output_text} for e in self.examples],
            "constraints": self.constraints,
            "function_signature": self.function_signature,
        }


@dataclass
class SubmissionResult:
    """提交判题结果"""
    submission_id: str
    problem_slug: str
    problem_title: str
    difficulty: str
    status: str                   # Accepted / Wrong Answer / TLE / ...
    status_code: int = 0          # 原始状态码
    frontend_id: str = ""         # 显示题号
    tags: list = field(default_factory=list)  # 题目标签
    runtime_ms: float = 0
    memory_mb: float = 0
    runtime_percentile: float = 0
    memory_percentile: float = 0
    language: str = "javascript"
    code: str = ""
    error_message: str = ""
    failed_testcase: str = ""
    expected_output: str = ""
    actual_output: str = ""
    total_correct: int = 0
    total_testcases: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def is_accepted(self) -> bool:
        return self.status == "Accepted"

    @property
    def passed_rate(self) -> str:
        if self.total_testcases == 0:
            return "N/A"
        return f"{self.total_correct}/{self.total_testcases}"

    def to_dict(self) -> dict:
        return {
            "submission_id": self.submission_id,
            "problem_id": self.frontend_id,
            "problem_slug": self.problem_slug,
            "problem_title": self.problem_title,
            "difficulty": self.difficulty,
            "tags": self.tags,
            "status": self.status,
            "status_code": self.status_code,
            "runtime_ms": self.runtime_ms,
            "memory_mb": self.memory_mb,
            "runtime_percentile": self.runtime_percentile,
            "memory_percentile": self.memory_percentile,
            "language": self.language,
            "passed": self.passed_rate,
            "error_message": self.error_message,
            "failed_testcase": self.failed_testcase,
            "expected_output": self.expected_output,
            "actual_output": self.actual_output,
            "code": self.code,
            "timestamp": self.timestamp,
        }


# 判题状态码映射
STATUS_MAP = {
    10: "Accepted",
    11: "Wrong Answer",
    12: "Memory Limit Exceeded",
    13: "Output Limit Exceeded",
    14: "Time Limit Exceeded",
    15: "Runtime Error",
    20: "Compile Error",
    21: "Unknown Error",
}
