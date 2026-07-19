#!/usr/bin/env python3
"""
统一测试运行器 — 自动发现并运行项目中所有测试。

用法:
    python scripts/run_tests.py              # 运行全部测试
    python scripts/run_tests.py --unit       # 仅运行单元测试
    python scripts/run_tests.py --fast       # 仅运行快速测试（跳过网络/慢速）
    python scripts/run_tests.py --coverage   # 带覆盖率报告
    python scripts/run_tests.py leetcode     # 仅运行指定模块测试
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # CalcTool/


def discover_test_dirs() -> list[str]:
    """自动发现所有测试目录"""
    dirs = []
    # 顶层 test/
    top_test = ROOT / "test"
    if top_test.exists():
        dirs.append(str(top_test))

    # fund/test/
    fund_test = ROOT / "fund" / "test"
    if fund_test.exists():
        dirs.append(str(fund_test))

    # local/app/*/test/
    local_app = ROOT / "local" / "app"
    if local_app.exists():
        for app_dir in local_app.iterdir():
            test_dir = app_dir / "test"
            if test_dir.exists() and test_dir.is_dir():
                dirs.append(str(test_dir))

    return dirs


def run_tests(
    test_dirs: list[str],
    markers: str = "",
    coverage: bool = False,
    verbose: bool = False,
    parallel: bool = False,
) -> int:
    """运行 pytest 并返回退出码"""
    cmd = [sys.executable, "-m", "pytest"]

    if verbose:
        cmd.append("-vv")
    else:
        cmd.append("-v")

    cmd.append("--tb=short")
    cmd.append("--timeout=120")
    cmd.append("--strict-markers")

    if markers:
        cmd.extend(["-m", markers])

    if coverage:
        cmd.extend([
            f"--cov-config={ROOT / '.coveragerc'}",
            "--cov",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-report=xml:coverage.xml",
        ])

    if parallel:
        cmd.extend(["-n", "auto"])

    cmd.extend(test_dirs)

    print(f"\n{'='*60}")
    print(f"Pytest command: {' '.join(cmd)}")
    print(f"{'='*60}\n")

    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def main():
    parser = argparse.ArgumentParser(description="统一测试运行器")
    parser.add_argument("module", nargs="?", help="指定模块名（如 leetcode / fund）")
    parser.add_argument("--unit", action="store_true", help="仅运行单元测试")
    parser.add_argument("--integration", action="store_true", help="仅运行集成测试")
    parser.add_argument("--fast", action="store_true", help="跳过网络和慢速测试")
    parser.add_argument("--coverage", action="store_true", help="生成覆盖率报告")
    parser.add_argument("--parallel", action="store_true", help="并行运行")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    args = parser.parse_args()

    # 确定测试目录
    if args.module:
        # 按模块名过滤测试目录
        all_dirs = discover_test_dirs()
        test_dirs = [d for d in all_dirs if args.module.lower() in Path(d).parent.name.lower()]
        if not test_dirs:
            test_dir = ROOT / "local" / "app" / args.module / "test"
            if test_dir.exists():
                test_dirs = [str(test_dir)]
            else:
                print(f"错误: 未找到模块 '{args.module}' 的测试目录")
                sys.exit(1)
    else:
        test_dirs = discover_test_dirs()

    if not test_dirs:
        print("未发现任何测试目录！")
        print("请在对应模块下创建 test/ 目录并放置 test_*.py 文件")
        sys.exit(0)

    print(f"发现 {len(test_dirs)} 个测试目录:")
    for d in test_dirs:
        print(f"  • {d}")

    # 构建标记
    markers = []
    if args.unit:
        markers.append("unit")
    if args.integration:
        markers.append("integration")
    if args.fast:
        markers.append("not (network or slow or skip_ci)")

    mark_str = " and ".join(markers) if markers else ""

    return run_tests(
        test_dirs=test_dirs,
        markers=mark_str,
        coverage=args.coverage,
        verbose=args.verbose,
        parallel=args.parallel,
    )


if __name__ == "__main__":
    sys.exit(main())
