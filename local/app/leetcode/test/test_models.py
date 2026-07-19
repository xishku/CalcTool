"""
LeetCode 模块单元测试 — models / fetcher / client / submitter / reporter
"""
import sys
import os
import json
import unittest
from pathlib import Path

# 确保模块路径可导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Problem, ProblemExample, SubmissionResult


class TestModels(unittest.TestCase):
    """数据模型单元测试"""

    def test_problem_example_default(self):
        e = ProblemExample(input_text="nums = [2,7]", output_text="[0,1]")
        self.assertEqual(e.input_text, "nums = [2,7]")
        self.assertEqual(e.output_text, "[0,1]")
        self.assertEqual(e.explanation, "")

    def test_problem_example_full(self):
        e = ProblemExample("a=1", "b=2", "因为 a+b=3")
        self.assertEqual(e.explanation, "因为 a+b=3")

    def test_problem_basic(self):
        p = Problem(
            question_id="1",
            frontend_id="1",
            title="Two Sum",
            title_slug="two-sum",
            difficulty="Easy",
            tags=["Array", "Hash Table"],
            content_html="<p>content</p>",
            content_text="content",
            function_signature="var twoSum = function(nums, target)",
            code_template="var twoSum = function(nums, target) {\n    \n};",
        )
        self.assertEqual(p.question_id, "1")
        self.assertEqual(p.frontend_id, "1")
        self.assertEqual(p.title, "Two Sum")
        self.assertEqual(p.difficulty, "Easy")
        self.assertEqual(len(p.tags), 2)

    def test_problem_to_dict(self):
        p = Problem(
            question_id="100",
            frontend_id="100",
            title="Same Tree",
            title_slug="same-tree",
            difficulty="Easy",
            tags=["Tree", "DFS"],
            content_text="Check if two trees are same",
            function_signature="var isSameTree = function(p, q)",
        )
        d = p.to_dict()
        self.assertEqual(d["question_id"], "100")
        self.assertEqual(d["frontend_id"], "100")
        self.assertIn("content_text", d)
        self.assertIn("examples", d)
        self.assertIn("constraints", d)
        self.assertIn("function_signature", d)

    def test_submission_result_accepted(self):
        r = SubmissionResult(
            submission_id="12345",
            problem_slug="two-sum",
            problem_title="Two Sum",
            difficulty="Easy",
            frontend_id="1",
            tags=["Array"],
            status="Accepted",
            status_code=10,
            runtime_ms=68.0,
            memory_mb=42.3,
            runtime_percentile=85.2,
            code="var twoSum = function(nums, target) { return []; };",
            total_correct=63,
            total_testcases=63,
        )
        self.assertTrue(r.is_accepted)
        self.assertEqual(r.passed_rate, "63/63")
        self.assertEqual(r.runtime_ms, 68.0)

    def test_submission_result_wrong_answer(self):
        r = SubmissionResult(
            submission_id="12346",
            problem_slug="add-two-numbers",
            problem_title="Add Two Numbers",
            difficulty="Medium",
            frontend_id="2",
            status="Wrong Answer",
            status_code=11,
            error_message="Output mismatch at test case 3",
            failed_testcase="[2,4,3]\n[5,6,4]",
            expected_output="[7,0,8]",
            actual_output="[7,0,9]",
            total_correct=2,
            total_testcases=10,
            code="// wrong code",
        )
        self.assertFalse(r.is_accepted)
        self.assertEqual(r.status, "Wrong Answer")
        self.assertEqual(r.passed_rate, "2/10")
        self.assertEqual(r.total_correct, 2)
        self.assertEqual(r.total_testcases, 10)

    def test_submission_result_to_dict(self):
        r = SubmissionResult(
            submission_id="99999",
            problem_slug="test-slug",
            problem_title="Test Problem",
            difficulty="Hard",
            frontend_id="999",
            tags=["DP", "Graph"],
            status="Accepted",
            runtime_ms=100.0,
            memory_mb=50.0,
            runtime_percentile=90.0,
            code="function solve() { return 42; }",
            total_correct=100,
            total_testcases=100,
        )
        d = r.to_dict()
        self.assertEqual(d["status"], "Accepted")
        self.assertIn("code", d)
        self.assertEqual(d["code"], "function solve() { return 42; }")
        self.assertIn("tags", d)
        self.assertIn("problem_id", d)

    def test_submission_result_passed_rate_na(self):
        r = SubmissionResult(
            submission_id="00000",
            problem_slug="na",
            problem_title="NA",
            difficulty="Easy",
            status="Pending",
        )
        self.assertEqual(r.passed_rate, "N/A")


class TestModelsEdgeCases(unittest.TestCase):
    """边界情况测试"""

    def test_empty_tags(self):
        p = Problem(
            question_id="0", frontend_id="0",
            title="Empty", title_slug="empty",
            difficulty="Medium",
        )
        self.assertEqual(p.tags, [])

    def test_empty_code_submission(self):
        r = SubmissionResult(
            submission_id="1",
            problem_slug="empty",
            problem_title="Empty Code",
            difficulty="Easy",
            status="Compile Error",
            status_code=20,
            error_message="No code submitted",
            code="",
        )
        self.assertFalse(r.is_accepted)
        self.assertEqual(r.code, "")

    def test_submission_without_percentile(self):
        r = SubmissionResult(
            submission_id="2",
            problem_slug="perf",
            problem_title="Perf Test",
            difficulty="Medium",
            status="Accepted",
            runtime_ms=50.0,
            memory_mb=30.0,
            runtime_percentile=0,
            memory_percentile=0,
        )
        self.assertTrue(r.is_accepted)
        self.assertEqual(r.runtime_percentile, 0)

    def test_problem_with_examples(self):
        p = Problem(
            question_id="5",
            frontend_id="5",
            title="Test",
            title_slug="test",
            difficulty="Hard",
            examples=[
                ProblemExample("in1", "out1", "exp1"),
                ProblemExample("in2", "out2"),
            ],
            constraints=["1 <= n <= 100"],
        )
        self.assertEqual(len(p.examples), 2)
        self.assertEqual(len(p.constraints), 1)
        self.assertEqual(p.examples[0].explanation, "exp1")


if __name__ == "__main__":
    unittest.main()
