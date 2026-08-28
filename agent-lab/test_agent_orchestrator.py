"""D6：多智能体编排（Orchestrator 分发 + 汇总）。

多智能体编排 = 一个主控 Agent（Orchestrator）把子任务分发给多个子
Agent，再汇总各子 Agent 的返回。这是 roadmap Phase 4 的差异化维度：
"mock 子 Agent 返回，断言分发/汇总逻辑"。

确定性实现，不依赖真实模型。子 Agent 全部用确定性 mock 替身。
"""
import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agentlab"))

from agentlab.orchestrator import (
    Orchestrator, MockSubAgent, SequentialOrchestrator,
)
from agentlab.tools import TOOLS, invoke_tool


# ---------- 工具 ----------

def test_unknown_tool_raises():
    """① 未定义的工具调用抛 KeyError。"""
    with pytest.raises(KeyError):
        invoke_tool("nonexistent_tool", {})


def test_tool_metadata_present():
    """② 每个工具带 description + parameters。"""
    for name, meta in TOOLS.items():
        assert "description" in meta
        assert "parameters" in meta


def test_tool_result_correct():
    """③ 工具返回确定结果。"""
    assert TOOLS["lookup"]["function"]("Beijing") == "北京 晴 25°C"


# ---------- Mock 子 Agent ----------

def test_mock_subagent_return():
    """④ 简单 Mock 子 Agent 返回固定值。"""
    sub = MockSubAgent(lambda q: "mock answer")
    assert sub.run("q") == "mock answer"


# ---------- 分发 ----------

def test_dispatch_all_tasks():
    """⑤ 分发器把所有子任务交给子 Agent。"""
    orchestrator = Orchestrator(
        sub_agents={"a": MockSubAgent(lambda q: "A")},
        routing={"t1": "a"},
    )
    outs = orchestrator.dispatch({"t1": "q"})
    assert outs["t1"] == "A"


def test_dispatch_uses_query():
    """⑥ 子 Agent 拿到真实问题查询。"""
    seen = {}

    def sub(q):
        seen["q"] = q
        return "ok"

    orchestrator = Orchestrator(
        sub_agents={"a": MockSubAgent(sub)},
        routing={"t1": "a"},
    )
    orchestrator.dispatch({"t1": "hello"})
    assert seen["q"] == "hello"
    assert orchestrator.dispatch({"t1": "hello"})["t1"] == "ok"


def test_dispatch_ignores_unknown_route():
    """⑦ 未路由的子任务不进输出字典（不抛错）。"""
    orchestrator = Orchestrator(
        sub_agents={},
        routing={},
    )
    outs = orchestrator.dispatch({"missing": "q"})
    assert "missing" not in outs
    assert outs == {}


# ---------- 终止 ----------

def test_orchestrator_stops_when_no_routing():
    """⑧ 空路由 → dispatch 返回空字典。"""
    orchestrator = Orchestrator(sub_agents={}, routing={})
    assert orchestrator.dispatch({"x": "q"}) == {}


# ---------- 汇总 ----------

def test_collect_results_all():
    """⑨ collect 用查询逐个喂给子 Agent，汇总结果。"""
    subs = [MockSubAgent(lambda q: "1"),
            MockSubAgent(lambda q: "2"),
            MockSubAgent(lambda q: "3")]
    orchestrator = Orchestrator(sub_agents={}, routing={})
    results = orchestrator.collect(subs, ["q1", "q2", "q3"])
    assert results == ["1", "2", "3"]


def test_collect_results_empty():
    """⑩ collect 空输入返回空列表。"""
    orchestrator = Orchestrator(sub_agents={}, routing={})
    assert orchestrator.collect([], []) == []


# ---------- 顺序编排 ----------

def test_sequential_runs_all():
    """⑪ SequentialOrchestrator 顺序跑完所有子 Agent。"""
    order = []

    def sub_a(q):
        order.append("a")
        return "A"

    def sub_b(q):
        order.append("b")
        return "B"

    orchestrator = SequentialOrchestrator(
        sub_agents={"a": MockSubAgent(sub_a), "b": MockSubAgent(sub_b)},
        sequence=["a", "b"],
    )
    result = orchestrator.run({"t1": "q"})
    assert result["output"] == "A+B"
    assert order == ["a", "b"]


def test_sequential_missing_agent():
    """⑫ 顺序编排里缺失的子 Agent → collect 时该位置为空。"""
    orchestrator = SequentialOrchestrator(
        sub_agents={"a": MockSubAgent(lambda q: "A")},
        sequence=["a", "missing"],
    )
    result = orchestrator.run({"t1": "q"})
    assert result["output"] == "A"


def test_sequential_stops_on_unknown():
    """⑬ 顺序编排里遇到未注册子 Agent → 终止并记录 reason。"""
    orchestrator = SequentialOrchestrator(
        sub_agents={},
        sequence=["missing"],
    )
    result = orchestrator.run({"t1": "q"})
    assert result["reason"] == "unknown_agent"
    assert result["output"] == ""
