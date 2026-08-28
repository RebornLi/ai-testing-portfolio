"""D7 工具集测试：验证工具正确性 + 未知工具错误 + 调用链。

全部确定性、不依赖模型。覆盖：
- 工具函数结果正确
- 未知工具抛错
- 工具调用链（多步顺序执行，前一步结果进入后一步）
"""
import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agentlab"))

from agentlab.tools import TOOLS, tool_names, invoke_tool
from agentlab.agent import ReActAgent, DeterministicPlanner


# ---------- 工具函数正确性 ----------

def test_add_tool():
    """① add 工具返回两数和。"""
    assert TOOLS["add"]["function"](2, 3) == 5
    assert TOOLS["add"]["function"](-1, 1) == 0


def test_multiply_tool():
    """② multiply 工具返回两数积。"""
    assert TOOLS["multiply"]["function"](3, 4) == 12
    assert TOOLS["multiply"]["function"](0, 5) == 0


def test_lookup_tool():
    """③ lookup 返回确定天气。"""
    assert "25" in TOOLS["lookup"]["function"]("beijing")
    assert "天气未知" in TOOLS["lookup"]["function"]("unknowntown")


def test_tool_names_deterministic():
    """④ 工具名列表确定且有序。"""
    names = tool_names()
    assert names == ["add", "lookup", "multiply"]


def test_unknown_tool_raises():
    """⑤ 调用未定义工具抛 KeyError（不是静默失败）。"""
    with pytest.raises(KeyError):
        invoke_tool("nonexistent_tool", {})


def test_tool_metadata_present():
    """⑥ 每个工具带 description + parameters 元数据。"""
    for name, meta in TOOLS.items():
        assert "description" in meta
        assert "parameters" in meta


# ---------- 工具调用链（多步）----------

def test_single_tool_call_chain():
    """⑦ 单个工具调用：agent.run 正确执行并记录结果。"""
    agent = ReActAgent(
        DeterministicPlanner([("tool", "add", {"a": 10, "b": 5}),
                              ("answer", "15")]),
        max_iterations=10,
    )
    res = agent.run("10 加 5 等于几？")
    assert res["answer"] == "15"
    assert len(res["trajectory"]) == 1
    assert res["trajectory"][0].result == 15


def test_multi_tool_call_chain_order():
    """⑧ 多步工具链：按顺序执行，前一步结果影响后一步。"""
    agent = ReActAgent(
        DeterministicPlanner([
            ("tool", "add", {"a": 3, "b": 4}),   # 7
            ("tool", "multiply", {"a": 7, "b": 2}),  # 14
            ("answer", "14"),
        ]),
        max_iterations=10,
    )
    res = agent.run("先 3+4，再乘 2")
    chain = [(c.name, c.args, c.result) for c in res["trajectory"]]
    assert chain == [
        ("add", {"a": 3, "b": 4}, 7),
        ("multiply", {"a": 7, "b": 2}, 14),
    ]


def test_sequence_end_when_exhausted():
    """⑩ 序列用尽仍未 answer → reason="sequence_end"，answer 为 None。"""
    agent = ReActAgent(
        DeterministicPlanner([("tool", "add", {"a": 1, "b": 1})]),
        max_iterations=10,
    )
    res = agent.run("跑完序列")
    assert res["reason"] == "sequence_end"
    assert res["answer"] is None
    assert len(res["trajectory"]) == 1


def test_tool_call_args_recorded():
    """⑨ 工具调用的参数被完整记录（便于断言入参）。"""
    agent = ReActAgent(
        DeterministicPlanner([("tool", "lookup", {"city": "Shanghai"}),
                              ("answer", "done")]),
        max_iterations=10,
    )
    res = agent.run("上海天气？")
    call = res["trajectory"][0]
    assert call.name == "lookup"
    assert call.args == {"city": "Shanghai"}
