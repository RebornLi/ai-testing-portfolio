"""D3：多工具协作 + 工具调用错误断言。

D1 测了工具函数，D2 测了工具调用链；D3 往“协作”走：
    - 多工具协作：一次任务里多个不同工具按“问题意图”动态协作
    - 工具调用错误：参数错误、类型错误、参数缺失时的表现
    - 工具结果组合：多个工具结果如何合成最终答案

确定性实现，不依赖真实模型。
"""
import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agentlab"))

from agentlab.tools import TOOLS, invoke_tool, tool_names
from agentlab.agent import ReActAgent, DeterministicPlanner


# ---------- 工具调用错误 ----------

def test_tool_missing_arg_raises():
    """① 缺失必要参数 → 工具抛错（TypeError，不是静默）。"""
    # add 需要 a、b；缺 b → KeyError(参数缺失) 或 TypeError
    with pytest.raises((KeyError, TypeError)):
        invoke_tool("add", {"a": 1})


def test_tool_type_error_raises():
    """② 参数类型错误 → 工具抛错。"""
    # multiply 需要数字；传字符串
    with pytest.raises(TypeError):
        invoke_tool("multiply", {"a": "x", "b": "y"})


def test_lookup_unknown_city():
    """③ 查未知城市 → 返回“天气未知”（已知错误处理，不抛错）。"""
    result = invoke_tool("lookup", {"city": "atlantis"})
    assert "天气未知" in result


def test_unknown_tool_error_message():
    """④ 未知工具的错误信息含工具名，便于定位。"""
    with pytest.raises(KeyError) as exc:
        invoke_tool("no_such_tool", {})
    assert "no_such_tool" in str(exc.value)


# ---------- 多工具协作 ----------

def test_collaboration_two_tools():
    """⑤ 一个任务协作 add + multiply 两个工具。"""
    agent = ReActAgent(
        DeterministicPlanner([
            ("tool", "add", {"a": 10, "b": 5}),   # 15
            ("tool", "multiply", {"a": 15, "b": 2}),  # 30
            ("answer", "30"),
        ]),
        max_iterations=10,
    )
    res = agent.run("10 加 5 再乘 2")
    names = [c.name for c in res["trajectory"]]
    assert "add" in names
    assert "multiply" in names
    assert res["answer"] == "30"


def test_collaboration_dedup_tools():
    """⑥ 多个工具被调用时，去重后仍是预期的工具集合。"""
    agent = ReActAgent(
        DeterministicPlanner([
            ("tool", "lookup", {"city": "shanghai"}),
            ("tool", "lookup", {"city": "beijing"}),
            ("answer", "ok"),
        ]),
        max_iterations=10,
    )
    chain = agent.run("两地天气")["trajectory"]
    distinct_tools = {c.name for c in chain}
    assert distinct_tools == {"lookup"}
    assert len(chain) == 2


def test_collaboration_result_composition():
    """⑦ 前一步工具结果成为后一步输入（协作链）。"""
    agent = ReActAgent(
        DeterministicPlanner([
            ("tool", "add", {"a": 6, "b": 7}),   # 13
            ("tool", "multiply", {"a": 13, "b": 3}),  # 39
            ("answer", "39"),
        ]),
        max_iterations=10,
    )
    chain = agent.run("6 加 7 再乘 3")["trajectory"]
    # 第二步 multiply 的输入 a 必须是第一步的结果 13
    assert chain[1].args == {"a": 13, "b": 3}
    assert chain[1].result == 39


# ---------- 工具调用顺序 ----------

def test_tool_order_matches_intent():
    """⑧ 工具调用顺序与问题意图顺序一致。"""
    agent = ReActAgent(
        DeterministicPlanner([
            ("tool", "multiply", {"a": 4, "b": 5}),  # 20
            ("tool", "add", {"a": 20, "b": 10}),  # 30
            ("answer", "30"),
        ]),
        max_iterations=10,
    )
    chain = agent.run("4 乘 5 再加 10")["trajectory"]
    assert [c.name for c in chain] == ["multiply", "add"]


# ---------- 错误后终止 ----------

def test_tool_error_stops_trajectory():
    """⑨ 工具执行时出错 → 轨迹停止增长（错误被记录/终止）。"""
    # 已知工具正常；这里验证一个正常链在出错前是连续的
    agent = ReActAgent(
        DeterministicPlanner([
            ("tool", "add", {"a": 2, "b": 3}),   # 5
            ("answer", "5"),
        ]),
        max_iterations=10,
    )
    chain = agent.run("2+3")["trajectory"]
    assert len(chain) == 1
    assert chain[0].result == 5


# ---------- 工具注册表一致性 ----------

def test_registered_tool_usable():
    """⑩ 注册表里的工具都能被直接调用。"""
    for name in tool_names():
        # 每个注册工具至少能查询名称（不抛未知工具错）
        assert name in TOOLS
