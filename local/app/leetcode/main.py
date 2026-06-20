"""
LeetCode 自动化刷题工具 — 主入口

用法:
    # 单题模式：指定 LeetCode 题目 slug
    python main.py --slug two-sum

    # 单题模式：指定题号
    python main.py --id 1

    # 批量模式：按难度过滤
    python main.py --batch --difficulty Easy --max 5

    # 批量模式：按标签过滤
    python main.py --batch --tags Array --max 10
"""
import argparse
import logging
import sys
from pathlib import Path

from config import load_config
from client import LeetCodeClient
from fetcher import Fetcher
from solver import create_solver
from submitter import Submitter
from reporter import Reporter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("leetcode")


def solve_single(
    fetcher: Fetcher,
    solver,
    submitter: Submitter,
    reporter: Reporter,
    title_slug: str,
) -> int:
    """单题模式：获取 → 解析 → 生成 → 提交 → 报告"""
    logger.info(f"=== 单题模式: {title_slug} ===")

    # 1. 获取题目
    try:
        problem = fetcher.get_problem_detail(title_slug)
        logger.info(f"题目: [{problem.frontend_id}] {problem.title} ({problem.difficulty})")
        logger.info(f"标签: {', '.join(problem.tags)}")
        logger.info(f"签名: {problem.function_signature}")
    except Exception as e:
        logger.error(f"获取题目失败: {e}")
        return 1

    # 2. 生成代码
    try:
        code = solver.solve(problem)
        print(f"\n{'─'*60}")
        print(f"生成的代码 ({len(code)} 字符):")
        print(f"{'─'*60}")
        print(code)
        print(f"{'─'*60}\n")
    except Exception as e:
        logger.error(f"代码生成失败: {e}")
        return 1

    # 3. 提交并判题
    try:
        result = submitter.submit(problem, code)
    except Exception as e:
        logger.error(f"提交失败: {e}")
        return 1

    # 4. 输出报告
    reporter.generate([result], format_type="csv")
    reporter.generate([result], format_type="markdown")
    reporter.print_summary([result])

    return 0 if result.is_accepted else 1


def solve_batch(
    fetcher: Fetcher,
    solver,
    submitter: Submitter,
    reporter: Reporter,
    difficulty: str = None,
    tags: list = None,
    max_problems: int = 10,
    start_from: int = 0,
) -> int:
    """批量模式"""
    logger.info(f"=== 批量模式 ===")
    logger.info(f"难度: {difficulty or '全部'}, 标签: {tags or '全部'}, 上限: {max_problems}")

    # 1. 获取题目列表
    page_size = min(max_problems, 50)
    list_data = fetcher.get_problem_list(
        skip=start_from,
        limit=page_size,
        difficulty=difficulty,
        tags=tags,
    )
    questions = list_data.get("questions", [])
    total = list_data.get("total", 0)
    logger.info(f"题库总计: {total} 题, 当前页: {len(questions)} 题")

    if not questions:
        logger.warning("没有匹配的题目")
        return 0

    questions = questions[:max_problems]

    # 2. 逐题处理
    results = []
    success = 0
    for i, q in enumerate(questions):
        slug = q.get("titleSlug", "")
        title = q.get("title", "")
        diff = q.get("difficulty", "")

        logger.info(f"\n{'─'*40}")
        logger.info(f"[{i+1}/{len(questions)}] {title} ({diff}) — {slug}")
        logger.info(f"{'─'*40}")

        try:
            problem = fetcher.get_problem_detail(slug)
            code = solver.solve(problem)
            result = submitter.submit(problem, code)
            results.append(result)
            if result.is_accepted:
                success += 1
        except Exception as e:
            logger.error(f"处理 {slug} 失败: {e}")
            from models import SubmissionResult
            results.append(SubmissionResult(
                submission_id="",
                problem_slug=slug,
                problem_title=title,
                difficulty=diff,
                status="Error",
                error_message=str(e),
            ))

    # 3. 输出报告
    reporter.generate(results, format_type="csv")
    reporter.generate(results, format_type="markdown")
    reporter.print_summary(results)

    return 0 if success == len(results) else 1


def main():
    parser = argparse.ArgumentParser(description="LeetCode 自动化刷题工具")
    parser.add_argument("--config", help="配置文件路径 (默认 config.yaml)")
    parser.add_argument("--slug", help="单题模式: 题目 slug，如 two-sum")
    parser.add_argument("--id", type=int, help="单题模式: 题目编号 (通过搜索获取 slug)")

    # 批量模式
    parser.add_argument("--batch", action="store_true", help="批量模式")
    parser.add_argument("--difficulty", choices=["Easy", "Medium", "Hard"], help="难度过滤")
    parser.add_argument("--tags", nargs="+", help="标签过滤，如 --tags Array DP")
    parser.add_argument("--max", type=int, default=10, help="最大处理题数 (默认 10)")
    parser.add_argument("--start", type=int, default=0, help="起始偏移 (默认 0)")

    # 输出
    parser.add_argument("--format", choices=["csv", "json", "markdown"], default="csv",
                        help="报告格式 (默认 csv)")
    parser.add_argument("--output", default="./output", help="输出目录")

    args = parser.parse_args()

    # 加载配置
    try:
        config = load_config(args.config)
    except Exception as e:
        logger.error(f"加载配置失败: {e}")
        return 1

    # 验证必要配置
    if not config.auth.cookie:
        logger.error("未配置 LeetCode Cookie！请在 config.yaml 中设置 auth.cookie")
        logger.error("从浏览器开发者工具 → Application → Cookies 复制完整 Cookie 字符串")
        return 1
    if config.llm.mode == "api" and not config.llm.api_key:
        logger.error("API 模式下未配置 LLM API Key！")
        logger.error("请在 config.yaml 中设置 llm.api_key 或设置环境变量 LLM_API_KEY")
        logger.error("或切换为浏览器模式：llm.mode = \"browser\"")
        return 1

    # 初始化组件
    client = LeetCodeClient(config)

    # 验证认证
    if not client.verify_auth():
        logger.error("LeetCode 认证失败，请检查 Cookie")
        return 1

    fetcher = Fetcher(client)
    solver = create_solver(config)
    submitter = Submitter(client)
    reporter = Reporter(args.output or config.output.directory)

    # 执行模式
    exit_code = 0
    try:
        if args.batch:
            exit_code = solve_batch(
                fetcher, solver, submitter, reporter,
                difficulty=args.difficulty,
                tags=args.tags,
                max_problems=args.max,
                start_from=args.start,
            )
        else:
            # 单题模式
            slug = args.slug
            if not slug and args.id:
                # 通过 ID 查找 slug：遍历列表匹配
                list_data = fetcher.get_problem_list(limit=100)
                for q in list_data.get("questions", []):
                    if q.get("frontendQuestionId") == str(args.id):
                        slug = q.get("titleSlug")
                        break
            if not slug:
                logger.error("请指定 --slug <题目slug> 或 --id <题号>")
                logger.error("示例: python main.py --slug two-sum")
                logger.error("示例: python main.py --id 1")
                logger.error("示例: python main.py --batch --difficulty Easy --max 5")
                return 1

            exit_code = solve_single(fetcher, solver, submitter, reporter, slug)
    finally:
        # 浏览器模式：关闭浏览器
        if hasattr(solver, 'close'):
            solver.close()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
