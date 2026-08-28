"""D7：ReAct Agent 核心测试（确定性规划器下测轨迹+终止+状态）。

ReAct = Reasoning + Acting。核心机制：
    每轮：看轨迹 → 规划器决定动作 → 执行工具 → 累积状态 → 重复
终止三态：
    - reason="stopped"        规划器给出 answer，正常结束
    - reason="sequence_end"   确定性序列耗尽仍未 answer
    - reason="max_iterations" 失控循环，超过阈值强终止

确定性实现，不依赖真实模型。
"""
import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agentlab"))

from agentlab.agent import ReActAgent, DeterministicPlanner, LoopingPlanner, ToolCall


# ---------- reason 终止态 ----------

def test_reason_stopped():
    """① 序列给出 answer → reason="stopped"。"""
    agent = ReActAgent(
        DeterministicPlanner([("tool", "add", {"a": 1, "b": 1}),
                              ("answer", "2")]),
        max_iterations=10,
    )
    res = agent.run("1+1")
    assert res["reason"] == "stopped"


def test_reason_sequence_end():
    """② 序列耗尽未给 answer → reason="sequence_end"，answer 为 None。"""
    agent = ReActAgent(
        DeterministicPlanner([("tool", "add", {"a": 1, "b": 1})]),
        max_iterations=10,
    )
    res = agent.run("跑完序列")
    assert res["reason"] == "sequence_end"
    assert res["answer"] is None


def test_reason_max_iterations():
    """③ 失控循环（只发工具不发 answer）→ reason="max_iterations"。"""
    agent = ReActAgent(LoopingPlanner(), max_iterations=5)
    res = agent.run("随便循环")
    assert res["reason"] == "max_iterations"


# ---------- 终止性（不死循环）----------

def test_termination_bounded():
    """④ 失控规划器也不会死循环：轨迹长度封顶为 max_iterations。"""
    agent = ReActAgent(LoopingPlanner(), max_iterations=7)
    res = agent.run("循环")
    assert len(res["trajectory"]) == 7


def test_termination_small_max():
    """⑤ 不同 max_iterations → 轨迹长度相应封顶。"""
    for n in (1, 3, 10):
        agent = ReActAgent(LoopingPlanner(), max_iterations=n)
        res = agent.run("循环")
        assert len(res["trajectory"]) == n


def test_no_infinite_loop_safety():
    """⑥ 即使规划器一直报同一个工具，最终一定以某个 reason 返回。"""
    agent = ReActAgent(LoopingPlanner(name="multiply",
                                      args={"a": 2, "b": 3}),
                       max_iterations=20)
    res = agent.run("死循环")
    assert res["reason"] in ("max_iterations", "sequence_end")
    assert len(res["trajectory"]) <= 20


# ---------- 轨迹记录 ----------

def test_trajectory_empty_when_no_tools():
    """⑦ 首个动作就是 answer → 轨迹为空。"""
    agent = ReActAgent(
        DeterministicPlanner([("answer", "直接回答")]),
        max_iterations=10,
    )
    res = agent.run("直接说")
    assert res["trajectory"] == []
    assert res["answer"] == "直接回答"


def test_trajectory_records_tool_calls():
    """⑧ 轨迹记录每一步 tool_call（name/args/result）。"""
    agent = ReActAgent(
        DeterministicPlanner([
            ("tool", "lookup", {"city": "guangzhou"}),
            ("answer", "ok"),
        ]),
        max_iterations=10,
    )
    res = agent.run("广州天气？")
    assert len(res["trajectory"]) == 1
    call = res["trajectory"][0]
    assert isinstance(call, ToolCall)
    assert call.name == "lookup"
    assert call.args == {"city": "guangzhou"}
    assert call.result is not None


def test_answer_only_no_trajectory():
    """⑨ 只有答案的任务无工具调用记录。"""
    agent = ReActAgent(
        DeterministicPlanner([("answer", "无操作")]),
        max_iterations=10,
    )
    res = agent.run("啥也别干")
    assert res["answer"] == "无操作"
    assert len(res["trajectory"]) == 0


# ---------- 状态传播 ----------

def test_state_accumulates_across_rounds():
    """⑩ 每轮把上一步结果注入 state，后续轮次可见。"""

    class RecorderPlanner:
        """第一轮返回工具；把 state 带进第二轮再回答。"""
        def __init__(self):
            self.round = 0

        def __call__(self, history, state):
            self.round += 1
            if self.round == 1:
                return {"tool": ("add", {"a": 2, "b": 3})}
            # 第二轮可见上一步结果 5
            assert "5" in state
            return {"answer": "5"}

    agent = ReActAgent(RecorderPlanner(), max_iterations=10)
    res = agent.run("2+3")
    assert res["answer"] == "5"


def test_trajectory_is_iterable_list():
    """⑪ 轨迹是可遍历的列表，元素带 repr 可读。"""
    agent = ReActAgent(
        DeterministicPlanner([("tool", "multiply", {"a": 4, "b": 5}),
                              ("answer", "20")]),
        max_iterations=10,
    )
    res = agent.run("4*5")
    assert isinstance(res["trajectory"], list)
    texts = [repr(c) for c in res["trajectory"]]
    assert any("multiply" in t for t in texts)


# ---------- 多步复合任务 ----------

def test_arithmetic_chain_correct():
    """⑫ 复合算术：((10 - 2) / 4) 用工具链计算。"""
    # 用 add 的负数近似减法：10 + (-2) = 8，再 / 4 用 multiply 1/4
    # 这里用确定性序列模拟：先 add(10, -2)=8，再 multiply(8, 0.25)=2
    agent = ReActAgent(
        DeterministicPlanner([
            ("tool", "add", {"a": 10, "b": -2}),  # 8
            ("tool", "multiply", {"a": 8, "b": 0.25}),  # 2
            ("answer", "2"),
        ]),
        max_iterations=10,
    )
    res = agent.run("10 减 2 除以 4")
    chain = [c.result for c in res["trajectory"]]
    assert chain == [8, 2]
    assert res["answer"] == "2"
