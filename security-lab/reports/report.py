"""report.py — 安全测试报告：把三维度打分汇总成结构化 + 可读输出。

供 CLI 入口 run_evaluation.py 调用。写进 reports/ 并打印到 stdout（供 CI 看）。
格式：to_dict / to_json / to_text / write（reports/evaluation_YYYYmmdd_HHMMSS.{json,txt}）
"""
import json, os
from datetime import datetime


class SecurityReport:
    """汇总三维度安全打分，生成报告。

    tests: list[dict] 每项 {name, score, passed, errors}
    total: 总分（三维度均值）
    """

    def __init__(self, tests, total, passed):
        self.tests = tests
        self.total = total
        self.passed = passed

    def to_dict(self):
        return {
            "total": round(self.total, 3),
            "passed": self.passed,
            "dimensions": [
                {"name": t["name"], "score": t["score"],
                 "passed": t["passed"], "errors": t["errors"]}
                for t in self.tests
            ],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def to_text(self):
        lines = [
            "=" * 48,
            "  安全测试报告  |  总分: %.3f  |  通过: %s" % (self.total, self.passed),
            "=" * 48,
        ]
        for t in self.tests:
            status = "PASS" if t["passed"] else "FAIL"
            lines.append("[%s] %-24s  得分: %.3f" % (status, t["name"], t["score"]))
            for err in t["errors"]:
                lines.append("    ! %s" % err)
        lines.append("=" * 48)
        lines.append("总计: %d / %d 维度通过" % (
            sum(1 for t in self.tests if t["passed"]), len(self.tests)))
        return "\n".join(lines)

    def to_json(self):
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def write(self, report_dir="reports"):
        os.makedirs(report_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = os.path.join(report_dir, "evaluation_%s.json" % ts)
        txt_path = os.path.join(report_dir, "evaluation_%s.txt" % ts)
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(self.to_json())
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(self.to_text())
        return json_path, txt_path
