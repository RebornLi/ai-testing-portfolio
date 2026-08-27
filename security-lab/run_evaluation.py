"""run_evaluation.py — CLI 一键入口：跑安全审计 + 写报告。

用法：
    python run_evaluation.py            # 跑审计，打印报告，写 reports/
    python run_evaluation.py --json     # 额外打印 JSON 报告
    python run_evaluation.py --dir out  # 报告输出目录

这是 W8 安全测试工程化的门面：一条命令跑通三维度安全审计（含对比打分）。
"""
import sys, os, argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from evaluate import run_security_audit
from reports.report import SecurityReport


def main():
    parser = argparse.ArgumentParser(description="安全审计流水线（三维度）")
    parser.add_argument("--json", action="store_true",
                        help="打印 JSON 报告")
    parser.add_argument("--dir", default="reports", help="报告输出目录")
    args = parser.parse_args()

    report = run_security_audit()

    # 打印可读报告到 stdout
    print(report.to_text())

    # 写报告文件
    json_path, txt_path = report.write(args.dir)

    # 退出码：安全达标 → 0，否则 1（供 CI 门禁）
    exit_code = 0 if report.passed else 1

    if args.json:
        print(report.to_json())
    print("\n报告已写入: %s | %s" % (json_path, txt_path))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
