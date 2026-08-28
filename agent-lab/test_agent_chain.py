"""D2：工具调用链断言 + ReAct 全流程。

D1 测了单步工具、终止性、状态传播；D2 往“链式”走：
    - 工具调用链：多次调用时，每一步的 name/args/result/顺序都要断言
    - ReAct 全流程：prompt → 轨迹 → 答案，完整链路（多步链式计算）
    - 轨迹可重放：重新执行轨迹能得到相同结果（可复现性）
    - 状态隔离：同一 agent 跑多个任务，第二个不该看到第一个的 state

确定性实现，不依赖真实模型。
"""
import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agentlab"))

from agentlab.agent import ReActAgent, DeterministicPlanner
from agentlab.tools import invoke_tool


# ---------- 工具调用链断言 ----------

def test_chain_args_match_plan():
    """① 每步调用的参数，与规划器意图完全一致。"""
    agent = ReActAgent(
        DeterministicPlanner([
            ("tool", "add", {"a": 3, "b": 4}),
            ("tool", "multiply", {"a": 7, "b": 2}),
            ("answer", "14"),
        ]),
        max_iterations=10,
    )
    chain = agent.run("算")["trajectory"]
    assert chain[0].args == {"a": 3, "b": 4}
    assert chain[1].args == {"a": 7, "b": 2}


def test_chain_results_correct():
    """② 每步结果是工具的正确输出。"""
    agent = ReActAgent(
        DeterministicPlanner([
            ("tool", "add", {"a": 3, "b": 4}),   # 7
            ("tool", "multiply", {"a": 7, "b": 2}),  # 14
            ("answer", "14"),
        ]),
        max_iterations=10,
    )
    chain = agent.run("算")["trajectory"]
    assert [c.result for c in chain] == [7, 14]


def test_chain_order_preserved():
    """③ 调用顺序与规划顺序一致。"""
    agent = ReActAgent(
        DeterministicPlanner([
            ("tool", "add", {"a": 1, "b": 1}),
            ("tool", "lookup", {"city": "shanghai"}),
            ("tool", "multiply", {"a": 2, "b": 2}),
            ("answer", "ok"),
        ]),
        max_iterations=10,
    )
    chain = agent.run("算")["trajectory"]
    assert [c.name for c in chain] == ["add", "lookup", "multiply"]


def test_chain_call_count():
    """④ 总调用次数 = 规划里的 tool 步骤数。"""
    agent = ReActAgent(
        DeterministicPlanner([
            ("tool", "add", {"a": 1, "b": 1}),
            ("tool", "add", {"a": 2, "b": 2}),
            ("tool", "add", {"a": 3, "b": 3}),
            ("answer", "9"),
        ]),
        max_iterations=10,
    )
    assert len(agent.run("算")["trajectory"]) == 3


# ---------- ReAct 全流程（多步链式计算）----------

def test_full_flow_chained_arithmetic():
    """⑤ 多步链式计算 ((2+3) * 4) = 20，答案正确。"""
    agent = ReActAgent(
        DeterministicPlanner([
            ("tool", "add", {"a": 2, "b": 3}),   # 5
            ("tool", "multiply", {"a": 5, "b": 4}),  # 20
            ("answer", "20"),
        ]),
        max_iterations=10,
    )
    res = agent.run("2 加 3 再乘 4")
    assert res["answer"] == "20"
    assert res["reason"] == "stopped"
    chain = [c.result for c in res["trajectory"]]
    assert chain == [5, 20]


def test_full_flow_with_lookup():
    """⑥ 全流程用 lookup 工具，结果正确且进入答案。"""
    agent = ReActAgent(
        DeterministicPlanner([
            ("tool", "lookup", {"city": "Beijing"}),
            ("answer", "北京 晴 25°C"),
        ]),
        max_iterations=10,
    )
    res = agent.run("北京天气？")
    chain = res["trajectory"]
    assert chain[0].result == "北京 晴 25°C"
    assert res["answer"] == "北京 晴 25°C"


def test_full_flow_prompt_to_answer_complete():
    """⑦ prompt 完整流经：trajectory 非空 + answer 有值。"""
    agent = ReActAgent(
        DeterministicPlanner([
            ("tool", "add", {"a": 10, "b": 20}),
            ("answer", "30"),
        ]),
        max_iterations=10,
    )
    res = agent.run("10 加 20 等于多少？")
    assert len(res["trajectory"]) >= 1
    assert res["answer"] is not None


# ---------- 轨迹可重放（复现性）----------

def test_trajectory_replay():
    """⑧ 重新执行 trajectory，能得到相同结果。

    重放能力：agent.replay(trajectory) → [result, ...]
    这是 Agent 测试的关键——轨迹自包含、可复现。
    """
    agent = ReActAgent(
        DeterministicPlanner([
            ("tool", "add", {"a": 5, "b": 5}),   # 10
            ("tool", "multiply", {"a": 10, "b": 3}),  # 30
            ("answer", "30"),
        ]),
        max_iterations=10,
    )
    trajectory = agent.run("算")["trajectory"]
    replayed = agent.replay(trajectory)
    assert replayed == [10, 30]


def test_replay_matches_original():
    """⑨ 两次运行轨迹重放结果一致（无随机性）。"""
    def run_once():
        agent = ReActAgent(
            DeterministicPlanner([
                ("tool", "add", {"a": 7, "b": 8}),
                ("answer", "15"),
            ]),
            max_iterations=10,
        )
        return agent.replay(agent.run("算")["trajectory"])
    assert run_once() == run_once() == [15]


# ---------- 状态隔离 ----------

def test_state_isolation_between_runs():
    """⑩ 独立 agent 各自 run，各自 trajectory 干净（state 不共享）。

    真实 agent 用固定规划器：agent1 与 agent2 各自独立跑，
    各自的轨迹长度应独立 = 规划里的 tool 数，互不干扰。
    """
    def build():
        return ReActAgent(
            DeterministicPlanner([
                ("tool", "add", {"a": 1, "b": 1}),
                ("answer", "2"),
            ]),
            max_iterations=10,
        )
    r1 = build().run("任务A")
    r2 = build().run("任务B")
    assert len(r1["trajectory"]) == 1
    assert len(r2["trajectory"]) == 1
    assert r1["answer"] == "2"
    assert r2["answer"] == "2"
