"""
报告输出模块 — 完整记录每道题的代码和结果，生成多格式总报告。

输出目录结构:
  output/{timestamp}/
    code/            ← 每道题的 JS 代码
    detail/          ← 每道题的完整 JSON（含代码、用例、判题详情）
    summary.csv      ← 汇总 CSV
    summary.md       ← 汇总 Markdown
    summary.json     ← 汇总 JSON（含所有代码）
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
    """完整结果报告生成器"""

    def __init__(self, output_dir: str = "./output"):
        self.output_dir = Path(output_dir)

    def generate(self, results: List[SubmissionResult]) -> str:
        """
        生成完整报告包。

        Returns:
            报告根目录路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        root = self.output_dir / timestamp
        root.mkdir(parents=True, exist_ok=True)

        code_dir = root / "code"
        detail_dir = root / "detail"
        code_dir.mkdir(exist_ok=True)
        detail_dir.mkdir(exist_ok=True)

        # 逐题保存代码和详情
        for r in results:
            self._save_code_file(r, code_dir)
            self._save_detail_json(r, detail_dir)

        # 生成三份总报告
        self._write_csv(results, root / "summary.csv")
        self._write_markdown(results, root / "summary.md")
        self._write_json(results, root / "summary.json")

        logger.info(f"完整报告已生成: {root}")
        logger.info(f"  ├── code/    ({len(results)} 个 .js 文件)")
        logger.info(f"  ├── detail/  ({len(results)} 个 .json 文件)")
        logger.info(f"  ├── summary.csv")
        logger.info(f"  ├── summary.md")
        logger.info(f"  └── summary.json")
        return str(root)

    # ── 单题文件 ─────────────────────────────────────────────────────

    def _save_code_file(self, r: SubmissionResult, code_dir: Path):
        """保存单题代码为 .js 文件"""
        label = f"{r.frontend_id}_{r.problem_slug}" if r.frontend_id else r.problem_slug
        # 文件名安全处理
        safe = label.replace("/", "_").replace("\\", "_")
        filepath = code_dir / f"{safe}.js"
        header = f"// {r.frontend_id}. {r.problem_title} | {r.difficulty}"
        if r.tags:
            header += f" | {', '.join(r.tags)}"
        header += f" | 状态: {r.status}"
        if r.is_accepted:
            header += f" | 耗时 {r.runtime_ms}ms | 内存 {r.memory_mb}MB | 击败 {r.runtime_percentile:.1f}%"
        lines = [header, ""]
        if r.code:
            lines.append(r.code)
        else:
            lines.append("// (无代码)")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _save_detail_json(self, r: SubmissionResult, detail_dir: Path):
        """保存单题完整详情 JSON"""
        label = f"{r.frontend_id}_{r.problem_slug}" if r.frontend_id else r.problem_slug
        safe = label.replace("/", "_").replace("\\", "_")
        filepath = detail_dir / f"{safe}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(r.to_dict(), f, ensure_ascii=False, indent=2)

    # ── CSV 汇总 ─────────────────────────────────────────────────────

    def _write_csv(self, results: List[SubmissionResult], filepath: Path):
        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow([
                "题号", "标题", "Slug", "难度", "标签", "状态",
                "耗时(ms)", "内存(MB)", "击败%", "通过用例",
                "提交ID", "错误信息",
            ])
            for r in results:
                w.writerow([
                    r.frontend_id,
                    r.problem_title,
                    r.problem_slug,
                    r.difficulty,
                    ", ".join(r.tags) if r.tags else "",
                    r.status,
                    f"{r.runtime_ms:.1f}" if r.is_accepted else "",
                    f"{r.memory_mb:.1f}" if r.is_accepted else "",
                    f"{r.runtime_percentile:.1f}" if r.runtime_percentile else "",
                    r.passed_rate,
                    r.submission_id,
                    r.error_message[:300] if r.error_message else "",
                ])

    # ── Markdown 汇总 ─────────────────────────────────────────────────

    def _write_markdown(self, results: List[SubmissionResult], filepath: Path):
        s = self._summary(results)
        lines = [
            "# LeetCode 刷题报告",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 📊 汇总",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 总题数 | {s['total']} |",
            f"| 通过数 | {s['accepted']} |",
            f"| 通过率 | {s['accepted_rate']:.1f}% |",
            f"| 平均耗时 | {s['avg_runtime']:.1f} ms |",
            f"| 平均内存 | {s['avg_memory']:.1f} MB |",
            "",
            "## 📈 难度分布",
        ]
        lines.append("| 难度 | 通过/总数 | 通过率 |")
        lines.append("|------|-----------|--------|")
        for diff, stats in s["by_difficulty"].items():
            if stats["total"] > 0:
                lines.append(f"| {diff} | {stats['accepted']}/{stats['total']} | {stats['rate']:.1f}% |")

        lines.extend(["", "## 📋 详细结果", ""])
        lines.append("| # | 标题 | 难度 | 状态 | 耗时 | 内存 | 击败 | 通过 | 备注 |")
        lines.append("|---|------|------|------|------|------|------|------|------|")
        for r in results:
            icon = "✅" if r.is_accepted else "❌"
            fid = r.frontend_id or "-"
            rt = f"{r.runtime_ms:.0f}ms" if r.is_accepted else "-"
            mem = f"{r.memory_mb:.1f}MB" if r.is_accepted else "-"
            pct = f"{r.runtime_percentile:.1f}%" if r.runtime_percentile else "-"
            note = ""
            if r.error_message:
                note = r.error_message[:80].replace("|", "/")
            elif r.failed_testcase:
                note = f"失败用例: {r.failed_testcase[:60]}"
            lines.append(
                f"| {fid} | {r.problem_title} | {r.difficulty} | {icon} {r.status} | "
                f"{rt} | {mem} | {pct} | {r.passed_rate} | {note} |"
            )

        # 每道题附带代码摘要
        lines.extend(["", "## 💻 代码清单", ""])
        for r in results:
            fid = f"{r.frontend_id}. " if r.frontend_id else ""
            icon = "✅" if r.is_accepted else "❌"
            lines.append(f"### {icon} {fid}{r.problem_title} `{r.problem_slug}`")
            lines.append(f"- **难度**: {r.difficulty}")
            if r.tags:
                lines.append(f"- **标签**: {', '.join(r.tags)}")
            lines.append(f"- **状态**: {r.status}")
            if r.is_accepted:
                lines.append(f"- **性能**: {r.runtime_ms:.0f}ms, {r.memory_mb:.1f}MB, 击败 {r.runtime_percentile:.1f}%")
            if r.error_message:
                lines.append(f"- **错误**: {r.error_message[:200]}")
            if r.failed_testcase and r.failed_testcase != r.error_message:
                lines.append(f"- **失败用例**:\n  ```\n  {r.failed_testcase[:500]}\n  ```")
            if r.code:
                lines.append(f"\n```javascript\n{r.code.strip()}\n```")
            else:
                lines.append("\n```\n// 无代码\n```")
            lines.append("")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    # ── JSON 汇总 ────────────────────────────────────────────────────

    def _write_json(self, results: List[SubmissionResult], filepath: Path):
        data = {
            "generated_at": datetime.now().isoformat(),
            "summary": self._summary(results),
            "results": [r.to_dict() for r in results],
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── 统计 ─────────────────────────────────────────────────────────

    def _summary(self, results: List[SubmissionResult]) -> dict:
        total = len(results)
        accepted = [r for r in results if r.is_accepted]
        accepted_count = len(accepted)

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
