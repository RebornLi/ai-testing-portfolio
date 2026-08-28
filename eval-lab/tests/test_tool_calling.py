"""D2 工具调用维度测试（6 个断言关注点 + 先失败后实现）。

先写会失败的断言 → 确认它抓住坏 Agent → 好 Agent 变绿。
"""
import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "evalagents"))

from evalagents.agent import ReActAgent, DeterministicPlanner
from evalagents.metrics import score_tool_calling, has_wrong_param_name


def good_steps():
    return [("tool", "add", {"a": 3, "b": 4}),
            ("tool", "multiply", {"a": 7, "b": 2}),
            ("answer", "结果是14")]


# ---------- 好 Agent：6 个断言全过 ----------

def test_tool_name_sequence():
    """① name + 顺序：轨迹恰好是 add→multiply。"""
    chain = ReActAgent(DeterministicPlanner(good_steps())).run("x")["trajectory"]
    assert [c.name for c in chain] == ["add", "multiply"]


def test_tool_args_and_result():
    """②③ 参数值 + 结果：add{3,4}→7、multiply{7,2}→14。"""
    chain = ReActAgent(DeterministicPlanner(good_steps())).run("x")["trajectory"]
    assert chain[0].args == {"a": 3, "b": 4}
    assert chain[1].args == {"a": 7, "b": 2}
    assert [c.result for c in chain] == [7, 14]


def test_tool_replay():
    """④ 重放结果可复现。"""
    chain = ReActAgent(DeterministicPlanner(good_steps())).run("x")["trajectory"]
    assert ReActAgent(DeterministicPlanner(good_steps())).replay(chain) == [7, 14]


def test_tool_final_answer():
    """⑥ 最终答案。"""
    ans = ReActAgent(DeterministicPlanner(good_steps())).run("x")["answer"]
    assert ans == "结果是14"


def test_tool_calling_score_perfect():
    """score_tool_calling 满分（四步全对）。"""
    chain = ReActAgent(DeterministicPlanner(good_steps())).run("x")["trajectory"]
    exp = [("add", {"a": 3, "b": 4}), ("multiply", {"a": 7, "b": 2})]
    assert score_tool_calling(chain, exp) == 1.0


# ---------- 坏 Agent：3 类错误都要被抓住 ----------

def test_bad_uses_wrong_tool():
    """错1：该 add 却去 weather —— 断言能抓住。"""
    bad = ReActAgent(DeterministicPlanner([
        ("tool", "weather", {"city": "beijing"}),
        ("tool", "lookup", {"city": "beijing"}),
        ("answer", "错"),
    ])).run("x")["trajectory"]
    assert "add" not in [c.name for c in bad]


def test_bad_wrong_param_name():
    """错2：参数名 cities 应为 city —— 断言能抓住。"""
    bad = ReActAgent(DeterministicPlanner([
        ("tool", "lookup", {"cities": "beijing"}),
        ("answer", "错"),
    ])).run("x")["trajectory"]
    assert has_wrong_param_name(bad, "cities") is True


def test_tool_calling_score_catches_bad():
    """坏 Agent（用错工具）score_tool_calling 应 < 1。"""
    bad = ReActAgent(DeterministicPlanner([
        ("tool", "weather", {"city": "beijing"}),
        ("answer", "错"),
    ])).run("x")["trajectory"]
    exp = [("add", {"a": 3, "b": 4}), ("multiply", {"a": 7, "b": 2})]
    assert score_tool_calling(bad, exp) < 1.0
