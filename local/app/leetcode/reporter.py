"""
报告输出模块 — 支持 CSV / JSON / Markdown 格式。
"""
import os
import csv
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List

from models import SubmissionResult

logger = logging.getLogger(__name__)


class Reporter:
    """结果报告生成器"""

    def __init__(self, output_dir: str = "./output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, results: List[SubmissionResult], format_type: str = "csv") -> str:
        """
        生成报告。

        Args:
            results: 提交结果列表
            format_type: 输出格式 csv / json / markdown

        Returns:
            输出文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        handlers = {
            "csv": self._write_csv,
            "json": self._write_json,
            "markdown": self._write_markdown,
        }
        handler = handlers.get(format_type, self._write_csv)
        ext = format_type if format_type != "markdown" else "md"
        filename = f"leetcode_report_{timestamp}.{ext}"
        filepath = self.output_dir / filename
        handler(results, filepath)
        logger.info(f"报告已生成: {filepath}")
        return str(filepath)

    def _write_csv(self, results: List[SubmissionResult], filepath: Path):
        """输出 CSV"""
        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["题号", "标题", "难度", "状态", "耗时(ms)", "内存(MB)",
                         "击败%", "通过用例", "错误信息"])
            for r in results:
                w.writerow([
                    r.problem_slug,
                    r.problem_title,
                    r.difficulty,
                    r.status,
                    r.runtime_ms if r.is_accepted else "",
                    r.memory_mb if r.is_accepted else "",
                    f"{r.runtime_percentile:.1f}" if r.runtime_percentile else "",
                    r.passed_rate,
                    r.error_message[:200] if r.error_message else "",
                ])

    def _write_json(self, results: List[SubmissionResult], filepath: Path):
        """输出 JSON"""
        data = {
            "generated_at": datetime.now().isoformat(),
            "summary": self._summary(results),
            "results": [r.to_dict() for r in results],
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _write_markdown(self, results: List[SubmissionResult], filepath: Path):
        """输出 Markdown"""
        s = self._summary(results)
        lines = [
            "# LeetCode 刷题报告",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 汇总",
            f"- 总题数: {s['total']}",
            f"- 通过数: {s['accepted']}",
            f"- 通过率: {s['accepted_rate']:.1f}%",
            f"- 平均耗时: {s['avg_runtime']:.1f} ms",
            f"- 平均内存: {s['avg_memory']:.1f} MB",
            "",
            "### 难度分布",
        ]
        for diff, stats in s["by_difficulty"].items():
            lines.append(f"- {diff}: {stats['accepted']}/{stats['total']} ({stats['rate']:.1f}%)")

        lines.extend(["", "## 详细结果", ""])
        lines.append("| 题目标识 | 难度 | 状态 | 耗时 | 内存 | 通过 | 备注 |")
        lines.append("|----------|------|------|------|------|------|------|")
        for r in results:
            icon = "✅" if r.is_accepted else "❌"
            lines.append(
                f"| {r.problem_title} | {r.difficulty} | {icon} {r.status} | "
                f"{r.runtime_ms:.0f}ms | {r.memory_mb:.1f}MB | "
                f"{r.passed_rate} | {r.error_message[:50]} |"
            )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _summary(self, results: List[SubmissionResult]) -> dict:
        """生成汇总统计"""
        total = len(results)
        accepted = [r for r in results if r.is_accepted]
        accepted_count = len(accepted)

        # 按难度统计
        by_diff = {}
        for diff in ["Easy", "Medium", "Hard"]:
            d_results = [r for r in results if r.difficulty == diff]
            d_accepted = [r for r in d_results if r.is_accepted]
            by_diff[diff] = {
                "total": len(d_results),
                "accepted": len(d_accepted),
                "rate": (len(d_accepted) / len(d_results) * 100) if d_results else 0,
            }

        avg_rt = sum(r.runtime_ms for r in accepted) / accepted_count if accepted_count else 0
        avg_mem = sum(r.memory_mb for r in accepted) / accepted_count if accepted_count else 0

        return {
            "total": total,
            "accepted": accepted_count,
            "accepted_rate": (accepted_count / total * 100) if total else 0,
            "avg_runtime": avg_rt,
            "avg_memory": avg_mem,
            "by_difficulty": by_diff,
        }

    def print_summary(self, results: List[SubmissionResult]):
        """控制台打印汇总"""
        s = self._summary(results)
        print(f"\n{'='*50}")
        print(f"  总题数: {s['total']} | 通过: {s['accepted']} | 通过率: {s['accepted_rate']:.1f}%")
        for diff, stats in s["by_difficulty"].items():
            if stats["total"] > 0:
                print(f"  {diff}: {stats['accepted']}/{stats['total']} ({stats['rate']:.1f}%)")
        if s["avg_runtime"] > 0:
            print(f"  平均耗时: {s['avg_runtime']:.1f}ms | 平均内存: {s['avg_memory']:.1f}MB")
        print(f"{'='*50}")
