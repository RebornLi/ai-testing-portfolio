"""run_evaluation.py — CLI 一键入口：跑完整四维度评测 + 写报告。

用法：
    python run_evaluation.py            # 跑评测，打印报告，写 reports/
    python run_evaluation.py --json     # 额外打印 JSON 报告
    python run_evaluation.py --dir out  # 报告输出目录

这是 W7 工程化的门面：一条命令跑通全部评测。
"""
import sys, os, argparse
# 本 CLI 与 evaluate.py、包 autoeval/ 同目录：加自己的目录进 sys.path。
sys.path.insert(0, os.path.dirname(__file__))

from evaluate import run_full_evaluation
from autoeval.reports.report import EvaluationReport


def main():
    parser = argparse.ArgumentParser(description="自动评测流水线（四维度）")
    parser.add_argument("--json", action="store_true", help="打印 JSON 报告")
    parser.add_argument("--dir", default="reports", help="报告输出目录")
    args = parser.parse_args()

    report = run_full_evaluation()

    # 打印可读报告到 stdout
    print(report.to_text())

    # 写报告文件
    json_path, txt_path = report.write(args.dir)

    # 退出码：全维度通过 → 0，否则 1（供 CI 门禁）
    exit_code = 0 if report.passed else 1

    if args.json:
        print(report.to_json())
    print("\n报告已写入: %s | %s" % (json_path, txt_path))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
