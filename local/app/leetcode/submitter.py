"""
代码提交与判题模块。
"""
import time
import json
import logging
from typing import Optional
from datetime import datetime

from client import LeetCodeClient
from models import Problem, SubmissionResult, STATUS_MAP

logger = logging.getLogger(__name__)


class Submitter:
    """提交代码到 LeetCode 并轮询判题结果"""

    # 判题状态常量
    STATE_PENDING = "PENDING"
    STATE_STARTED = "STARTED"
    STATE_SUCCESS = "SUCCESS"

    def __init__(self, client: LeetCodeClient):
        self.client = client

    def submit(
        self,
        problem: Problem,
        code: str,
        poll_interval: float = 2.0,
        max_wait_seconds: float = 60.0,
    ) -> SubmissionResult:
        """
        提交代码并等待判题结果。

        Args:
            problem: 题目信息
            code: JavaScript 代码
            poll_interval: 轮询间隔（秒）
            max_wait_seconds: 最大等待时间（秒）

        Returns:
            SubmissionResult
        """
        # 1. 提交代码
        submission_id = self._submit_code(problem, code)
        logger.info(f"代码已提交，submission_id: {submission_id}")

        # 2. 轮询判题结果
        start_time = time.monotonic()
        result = None

        while time.monotonic() - start_time < max_wait_seconds:
            time.sleep(poll_interval)
            resp = self._check_result(submission_id)
            state = resp.get("state", "")

            if state == self.STATE_STARTED:
                logger.debug("判题中...")
                continue
            if state == self.STATE_PENDING:
                logger.debug("排队中...")
                continue
            if state == self.STATE_SUCCESS:
                result = self._parse_result(resp, submission_id, problem, code)
                break

        if result is None:
            logger.warning("判题超时，标记为 Unknown")
            result = SubmissionResult(
                submission_id=submission_id,
                problem_slug=problem.title_slug,
                problem_title=problem.title,
                difficulty=problem.difficulty,
                frontend_id=problem.frontend_id,
                tags=problem.tags,
                status="Timeout",
                code=code,
            )

        self._log_result(result)
        return result

    def _submit_code(self, problem: Problem, code: str) -> str:
        """通过 API 提交代码"""
        url = f"{self.client.base_url}/problems/{problem.title_slug}/submit/"
        payload = {
            "lang": "javascript",
            "question_id": problem.question_id,
            "typed_code": code,
        }
        resp = self.client.post(url, json=payload)
        data = resp.json()
        submission_id = data.get("submission_id")
        if not submission_id:
            raise RuntimeError(f"提交失败，响应: {data}")
        return str(submission_id)

    def _check_result(self, submission_id: str) -> dict:
        """查询判题结果"""
        url = f"{self.client.base_url}/submissions/detail/{submission_id}/check/"
        resp = self.client.get(url)
        return resp.json()

    def _parse_result(
        self,
        resp: dict,
        submission_id: str,
        problem: Problem,
        code: str,
    ) -> SubmissionResult:
        """解析判题响应为 SubmissionResult"""
        status_code = resp.get("status_code", 21)
        status_msg = resp.get("status_msg", "")
        runtime_msg = resp.get("status_runtime", "0 ms")
        memory_msg = resp.get("status_memory", "0 MB")
        runtime_percentile = resp.get("runtime_percentile", 0)
        memory_percentile = resp.get("memory_percentile", 0)
        error = resp.get("runtime_error", "")
        last_testcase = resp.get("last_testcase", "")
        expected = resp.get("expected_output", "")
        actual = resp.get("code_output", "")
        total_correct = resp.get("total_correct", 0)
        total_testcases = resp.get("total_testcases", 0)

        # 提取数值
        runtime_ms = self._parse_number(runtime_msg)
        memory_mb = self._parse_number(memory_msg)

        return SubmissionResult(
            submission_id=submission_id,
            problem_slug=problem.title_slug,
            problem_title=problem.title,
            difficulty=problem.difficulty,
            frontend_id=problem.frontend_id,
            tags=problem.tags,
            status=STATUS_MAP.get(status_code, status_msg or f"Unknown({status_code})"),
            status_code=status_code,
            runtime_ms=runtime_ms,
            memory_mb=memory_mb,
            runtime_percentile=float(runtime_percentile) if runtime_percentile else 0,
            memory_percentile=float(memory_percentile) if memory_percentile else 0,
            language="javascript",
            code=code,
            error_message=error or "",
            failed_testcase=last_testcase or "",
            expected_output=expected or "",
            actual_output=actual or "",
            total_correct=total_correct or 0,
            total_testcases=total_testcases or 0,
            timestamp=datetime.now().isoformat(),
        )

    @staticmethod
    def _parse_number(text: str) -> float:
        """从字符串中提取数字，如 "68 ms" -> 68.0, "42.3 MB" -> 42.3"""
        import re
        m = re.search(r"[\d.]+", str(text))
        return float(m.group()) if m else 0.0

    @staticmethod
    def _log_result(result: SubmissionResult):
        """记录结果日志"""
        icon = "✓" if result.is_accepted else "✗"
        msg = f"{icon} {result.problem_title} [{result.difficulty}] → {result.status}"
        if result.is_accepted:
            msg += f" | 耗时 {result.runtime_ms}ms | 内存 {result.memory_mb}MB"
            if result.runtime_percentile:
                msg += f" | 击败 {result.runtime_percentile:.1f}%"
        else:
            detail = result.error_message[:100] if result.error_message else ""
            if result.failed_testcase:
                detail = f"用例: {result.failed_testcase[:100]}"
            msg += f" | {detail}"
        logger.info(msg)
