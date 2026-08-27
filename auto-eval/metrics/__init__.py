"""metrics.py — 自动评测：四维度指标封装（离线确定性）

把 W6 的四个评测维度封装成可复用的指标类。每个指标提供一个
`score(...)` 方法，返回 (score, passed, errors)：
  - score: 0.0-1.0 的归一化得分
  - passed: True/False 表示该维度是否达标（阈值内）
  - errors: list[str] 该维度未达标的具体原因（达标时为空列表）

指标之间**相互独立**，便于组合、排序、进 CI。
"""


class ToolCallingMetric:
    """维度1：工具调用 —— 工具名 + 参数值 + 参数名 + 调用顺序都正确。

    expected = list[dict] 表示期望的工具调用链，
    每项 {"name": str, "args": dict, "result": (optional)}。
    """

    def __init__(self, expected, threshold=1.0):
        self.expected = expected
        self.threshold = threshold
        self.errors = []

    def score(self, trajectory):
        actual = [{"name": c.name, "args": c.args, "result": c.result}
                  for c in trajectory]
        if len(actual) != len(self.expected):
            self.errors.append(f"调用次数 {len(actual)} != 期望 {len(self.expected)}")
        # 逐位置比对：name + args（值和键）+ 顺序
        for i, (a, e) in enumerate(zip(actual, self.expected)):
            if a["name"] != e["name"]:
                self.errors.append(f"步骤{i} 工具名 {a['name']} != {e['name']}")
            if a["args"] != e["args"]:
                self.errors.append(f"步骤{i} 参数 {a['args']} != {e['args']}")
            if "result" in e and a["result"] != e["result"]:
                self.errors.append(f"步骤{i} 结果 {a['result']} != {e['result']}")
        passed = len(self.errors) == 0
        score = 1.0 if passed else 0.0
        return score, passed, self.errors


class MemoryMetric:
    """维度2：记忆 —— 记住的信息跨轮能被读取。

    memory: Memory 实例（跨轮存活）
    expected: dict 期望记忆内容
    """

    def __init__(self, memory, expected, threshold=1.0):
        self.memory, self.expected, self.threshold = memory, expected, threshold
        self.errors = []

    def score(self):
        score, passed = 1.0, True
        for key, value in self.expected.items():
            got = self.memory.read(key)
            if got != value:
                self.errors.append(f"忘记 {key}: 期望 {value} 实际 {got}")
                score, passed = 0.0, False
        return score, passed, self.errors


class CostLatencyMetric:
    """维度3：成本 & 延迟 —— 在预算内完成任务。

    成本 budget 元，延迟 budget 秒。超出则不达标。
    """

    def __init__(self, cost, latency, cost_budget=1.0, latency_budget=5.0):
        self.cost, self.latency = cost, latency
        self.cost_budget, self.latency_budget = cost_budget, latency_budget
        self.errors = []

    def score(self):
        score, passed = 1.0, True
        if self.cost > self.cost_budget:
            self.errors.append(f"成本 {self.cost:.4f} > 预算 {self.cost_budget}")
            score, passed = 0.0, False
        if self.latency > self.latency_budget:
            self.errors.append(f"延迟 {self.latency:.4f}s > 预算 {self.latency_budget}s")
            score, passed = 0.0, False
        # 归一化得分：成本/延迟越低分越高（不覆盖"是否达标"）
        score = max(score, 1 - self.cost / self.cost_budget, 1 - self.latency / self.latency_budget)
        return score, passed, self.errors


class DeepEvalMetric:
    """维度4：DeepEval 集成 —— LLM 断言（需 key；离线兜底确定性规则）。

    无 key 时走确定性兜底：答案包含关键词即通过（= W6 确定性 metric）。
    """

    def __init__(self, actual, expected, keyword=None):
        self.actual, self.expected, self.keyword = actual, expected, keyword
        self.errors = []

    def score(self):
        if self.keyword is None:
            # 无关键词兜底：实际输出 == 预期输出
            passed = self.actual == self.expected
            if not passed:
                self.errors.append(f"实际 {self.actual!r} != 预期 {self.expected!r}")
        else:
            passed = self.keyword in self.actual
            if not passed:
                self.errors.append(f"关键词 {self.keyword} 未命中 {self.actual!r}")
        return (1.0 if passed else 0.0), passed, self.errors


def evaluate_dimensions(results):
    """组合四维度，返回 {维度: (score, passed)} 与总分。

    results: list[dict] 每项 {name, score, passed, errors}
    总分 = 各维度得分均值。
    """
    summary = {r["name"]: (round(r["score"], 3), r["passed"]) for r in results}
    total = round(sum(r["score"] for r in results) / len(results), 3)
    return summary, total


def build_summary(report):
    """把评估报告转成可读文本（供 CI 日志 / 报告文件）。

    report: dict，含 tests 列表与 total 字段。
    """
    lines = [f"自动评测报告  总分={report['total']:.3f}  通过={report['passed']}"]
    lines.append("-" * 32)
    for t in report["tests"]:
        status = "PASS" if t["passed"] else "FAIL"
        lines.append(f"[{status}] {t['name']}  得分={t['score']:.3f}")
        for err in t["errors"]:
            lines.append(f"    ! {err}")
    return "\n".join(lines)
