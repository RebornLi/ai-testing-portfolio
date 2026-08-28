"""evaluate.py — 评测引擎：把被测 agent + 测试场景跑一遍，汇总四维度打分。

这是"一键评测"的引擎。run_evaluation.py 负责构建场景并打印报告，
本模块负责"执行 + 打分"两件事，分离以便单元测试。
"""
import sys, os

# evaluate.py 位于 auto-eval/ 根级。包 autoeval/ 与根同级：
# 把本文件所在目录加进 sys.path，即可 `from autoeval.X import ...`。
sys.path.insert(0, os.path.dirname(__file__))

from autoeval.agent import (
    ReActAgent, DeterministicPlanner, Memory, MemoryAgent,
)
from autoeval.metrics import (
    ToolCallingMetric, MemoryMetric, CostLatencyMetric, DeepEvalMetric,
)


def run_tool_calling_case(steps, tool_expected, max_iter=10):
    """运行一个工具调用场景，返回 {name, score, passed, errors}。

    ★ 关键：DeterministicPlanner 是【有状态】的，一次 run 就耗尽。
      轨迹用轨迹，answer 用【另一个】新 agent 取，绝不能复用同一 agent。
    """
    agent = ReActAgent(DeterministicPlanner(list(steps)), max_iterations=max_iter)
    traj = agent.run("算")["trajectory"]
    score, passed, errors = ToolCallingMetric(tool_expected).score(traj)
    answer = ReActAgent(DeterministicPlanner(list(steps))).run("算")["answer"]
    return {"name": "工具调用", "score": score, "passed": passed, "errors": errors,
            "answer": answer, "replay": agent.replay(traj)}


def run_memory_case(memory, expected, answer):
    """运行一个记忆场景。"""
    score, passed, errors = MemoryMetric(memory, expected).score()
    return {"name": "记忆", "score": score, "passed": passed,
            "errors": errors, "answer": answer}


def run_cost_case(cost, latency, cost_budget=1.0, latency_budget=5.0):
    """运行一个成本/延迟场景。"""
    score, passed, errors = CostLatencyMetric(
        cost, latency, cost_budget, latency_budget).score()
    return {"name": "成本延迟", "score": score, "passed": passed, "errors": errors,
            "cost": cost, "latency": latency}


def run_deepeval_case(actual, expected, keyword=None):
    """运行一个 DeepEval 离线兜底场景。"""
    score, passed, errors = DeepEvalMetric(actual, expected, keyword).score()
    return {"name": "DeepEval", "score": score, "passed": passed, "errors": errors,
            "actual": actual, "expected": expected}


def run_full_evaluation():
    """跑完整四维度评测，返回 EvaluationReport（供 run_evaluation.py 打印）。

    返回 report 对象的 dict 形式，便于测试断言（不写文件）。
    """
    from autoeval.reports.report import EvaluationReport

    # 维度1：工具调用（好 agent，应通过）
    tc = run_tool_calling_case(
        [("tool", "add", {"a": 3, "b": 4}),
         ("tool", "multiply", {"a": 7, "b": 2}),
         ("answer", "结果是14")],
        tool_expected=[
            {"name": "add", "args": {"a": 3, "b": 4}, "result": 7},
            {"name": "multiply", "args": {"a": 7, "b": 2}, "result": 14},
        ],
    )

    # 维度2：记忆（好 agent 跨轮存活）
    mem = Memory()
    class RememberingPlanner:
        turn = 1
        def __call__(self, prompt, memory, maxit):
            if self.turn == 1:
                memory.write("name", "小明"); memory.write("city", "北京")
                self.turn += 1
                return {"answer": "记下"}
            city = memory.read("city"); self.turn += 1
            return {"answer": f"你喜欢{city}" if city else "忘了"}
    planner = RememberingPlanner()
    MemoryAgent(mem, planner).run("第1轮")
    MemoryAgent(mem, planner).run("第2轮")
    mem_answer = MemoryAgent(mem, planner).run("第3轮")["answer"]
    mem = run_memory_case(mem, {"name": "小明", "city": "北京"}, mem_answer)

    # 维度3：成本/延迟（都在预算内）
    cost = run_cost_case(cost=0.5, latency=1.0)

    # 维度4：DeepEval 离线兜底
    ee = run_deepeval_case(actual="我喜欢北京", expected="北京", keyword="北京")

    tests = [tc, mem, cost, ee]
    total = sum(t["score"] for t in tests) / len(tests)
    passed = sum(1 for t in tests if t["passed"]) == len(tests)
    return EvaluationReport(tests, total, passed)
