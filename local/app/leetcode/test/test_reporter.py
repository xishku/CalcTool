"""
LeetCode Reporter 模块单元测试 — 报告生成功能
"""
import sys
import os
import json
import csv
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from models import SubmissionResult
from reporter import Reporter


class TestReporter(unittest.TestCase):
    """报告生成器测试"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.reporter = Reporter(output_dir=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_result(self, slug, title, diff, status, **kwargs):
        defaults = {
            "submission_id": f"sid_{slug}",
            "problem_slug": slug,
            "problem_title": title,
            "difficulty": diff,
            "status": status,
            "code": "function solve() { return 42; }",
        }
        defaults.update(kwargs)
        return SubmissionResult(**defaults)

    def test_generate_creates_directory_structure(self):
        results = [
            self._make_result("two-sum", "Two Sum", "Easy", "Accepted",
                              frontend_id="1", runtime_ms=68.0, memory_mb=42.0,
                              runtime_percentile=85.0, total_correct=63, total_testcases=63),
        ]
        root = self.reporter.generate(results)
        root_path = Path(root)

        self.assertTrue(root_path.exists())
        self.assertTrue((root_path / "code").exists())
        self.assertTrue((root_path / "detail").exists())
        self.assertTrue((root_path / "summary.csv").exists())
        self.assertTrue((root_path / "summary.md").exists())
        self.assertTrue((root_path / "summary.json").exists())

    def test_generate_code_files(self):
        results = [
            self._make_result("two-sum", "Two Sum", "Easy", "Accepted",
                              frontend_id="1", code="function twoSum() {}"),
            self._make_result("add-two-numbers", "Add Two Numbers", "Medium", "Wrong Answer",
                              frontend_id="2", code="function addTwo() {}"),
        ]
        root = self.reporter.generate(results)
        code_dir = Path(root) / "code"

        js_files = list(code_dir.glob("*.js"))
        self.assertEqual(len(js_files), 2)

    def test_generate_detail_json(self):
        results = [
            self._make_result("two-sum", "Two Sum", "Easy", "Accepted",
                              frontend_id="1", code="function test() {}",
                              tags=["Array", "Hash Table"]),
        ]
        root = self.reporter.generate(results)
        detail_dir = Path(root) / "detail"

        json_files = list(detail_dir.glob("*.json"))
        self.assertEqual(len(json_files), 1)

        with open(json_files[0], encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["status"], "Accepted")
            self.assertIn("code", data)

    def test_generate_csv_has_headers(self):
        results = [
            self._make_result("two-sum", "Two Sum", "Easy", "Accepted",
                              frontend_id="1", runtime_ms=50.0, memory_mb=30.0,
                              total_correct=63, total_testcases=63),
        ]
        root = self.reporter.generate(results)
        csv_path = Path(root) / "summary.csv"

        with open(csv_path, encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader)
            self.assertIn("题号", header)
            self.assertIn("状态", header)
            self.assertIn("通过用例", header)
            rows = list(reader)
            self.assertEqual(len(rows), 1)

    def test_generate_markdown_contains_summary(self):
        results = [
            self._make_result("two-sum", "Two Sum", "Easy", "Accepted",
                              frontend_id="1", runtime_ms=60.0, memory_mb=40.0,
                              runtime_percentile=80.0, total_correct=63, total_testcases=63),
            self._make_result("test", "Test", "Medium", "Wrong Answer",
                              frontend_id="2", error_message="mismatch"),
        ]
        root = self.reporter.generate(results)
        md_path = Path(root) / "summary.md"

        content = md_path.read_text(encoding="utf-8")
        self.assertIn("总题数", content)
        self.assertIn("通过率", content)
        self.assertIn("Two Sum", content)
        self.assertIn("Test", content)
        self.assertIn("function solve()", content)  # 代码块

    def test_generate_json_has_summary(self):
        results = [
            self._make_result("two-sum", "Two Sum", "Easy", "Accepted",
                              frontend_id="1", runtime_ms=50.0, memory_mb=30.0,
                              total_correct=63, total_testcases=63),
        ]
        root = self.reporter.generate(results)
        json_path = Path(root) / "summary.json"

        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
            self.assertIn("summary", data)
            self.assertIn("results", data)
            self.assertEqual(data["summary"]["total"], 1)
            self.assertEqual(data["summary"]["accepted"], 1)

    def test_generate_with_error_results(self):
        results = [
            self._make_result("err1", "Error One", "Hard", "Runtime Error",
                              frontend_id="100", status_code=15,
                              error_message="Division by zero",
                              failed_testcase="[0]", expected_output="1", actual_output="error"),
        ]
        root = self.reporter.generate(results)
        md_path = Path(root) / "summary.md"
        content = md_path.read_text(encoding="utf-8")
        self.assertIn("Division by zero", content)

    def test_print_summary_does_not_crash(self):
        results = [
            self._make_result("a", "A", "Easy", "Accepted",
                              frontend_id="1", runtime_ms=10.0, memory_mb=20.0),
        ]
        # 不应抛出异常
        self.reporter.print_summary(results)

    def test_empty_results(self):
        root = self.reporter.generate([])
        csv_path = Path(root) / "summary.csv"
        content = csv_path.read_text(encoding="utf-8-sig")
        # 至少要有表头
        self.assertIn("题号", content)


if __name__ == "__main__":
    unittest.main()
