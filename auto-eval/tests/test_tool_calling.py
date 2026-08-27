"""测试维度1：工具调用评测（复用 W4 确定性 agent + metrics.ToolCallingMetric）。

指标 API：score() 返回 (score, passed, errors) 三元组。
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "system"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent import ReActAgent, DeterministicPlanner, LoopingPlanner
from metrics import ToolCallingMetric, evaluate_dimensions


def build(steps, max_iter=10):
    return ReActAgent(DeterministicPlanner(steps), max_iterations=max_iter)


def test_tool_calling_good_passes():
    """好 agent：加乘链正确（name/args/result/顺序 全对）"""
    agent = build([
        ("tool", "add", {"a": 3, "b": 4}),
        ("tool", "multiply", {"a": 7, "b": 2}),
        ("answer", "结果是14"),
    ])
    traj = agent.run("算")["trajectory"]
    expected = [
        {"name": "add", "args": {"a": 3, "b": 4}, "result": 7},
        {"name": "multiply", "args": {"a": 7, "b": 2}, "result": 14},
    ]
    score, passed, errors = ToolCallingMetric(expected).score(traj)
    assert passed and score == 1.0, (score, passed)
    assert errors == []


def test_tool_calling_wrong_args_fails():
    """坏 agent：参数错误 → 抓出来。"""
    agent = build([
        ("tool", "add", {"a": 1, "b": 2}),
        ("answer", "错"),
    ])
    traj = agent.run("算")["trajectory"]
    expected = [
        {"name": "add", "args": {"a": 3, "b": 4}, "result": 7},
    ]
    score, passed, errors = ToolCallingMetric(expected).score(traj)
    assert not passed and score == 0.0
    assert any("参数" in e for e in errors)


def test_tool_calling_missing_call_fails():
    """坏 agent：漏掉一步 → 次数不匹配被抓住。"""
    agent = build([
        ("tool", "add", {"a": 3, "b": 4}),
        ("answer", "只加"),
    ])
    traj = agent.run("算")["trajectory"]
    expected = [
        {"name": "add", "args": {"a": 3, "b": 4}, "result": 7},
        {"name": "multiply", "args": {"a": 7, "b": 2}, "result": 14},
    ]
    score, passed, errors = ToolCallingMetric(expected).score(traj)
    assert not passed and score == 0.0
    assert any("次数" in e for e in errors)
