"""D3 任务完成率 + 多轮上下文测试（好/坏 Agent 对比）。

好 Agent 完成率 100%、第 3 轮记得"北京"、记忆有内容；
坏 Agent 完成率 <100%、记忆空、第三轮答"不记得"。
"""
import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "evalagents"))

from evalagents.agent import MemoryAgent, DeterministicPlanner
from evalagents.metrics import completion_rate, score_context_memory


# ---------- D3 任务完成率 ----------

def test_completion_rate_good_is_100():
    """好 Agent：add→multiply→answer → 100%。"""
    good = ["add", "multiply", "answer"]
    assert completion_rate(good, ["add", "multiply", "answer"]) == 1.0


def test_completion_rate_bad_is_67():
    """坏 Agent：add→answer（漏 multiply）→ 67%。"""
    bad = ["add", "answer"]
    assert completion_rate(bad, ["add", "multiply", "answer"]) == 2 / 3


# ---------- D3 多轮上下文 / 记忆 ----------

class RememberingPlanner:
    """记住第 1 轮内容，第 3 轮考问从 memory 读出。"""
    def __init__(self):
        self.turn = 1

    def __call__(self, prompt, trajectory, state, memory):
        if self.turn == 1:
            memory.write("user_name", "小明")
            memory.write("favorite_city", "北京")
            self.turn += 1
            return {"answer": "好的，我记住了"}
        if self.turn == 3:
            city = memory.read("favorite_city")
            self.turn += 1
            return {"answer": f"你之前说喜欢{city}" if city else "我不记得"}
        self.turn += 1
        return {"answer": "等待"}


class ForgettingPlanner:
    """永远不写 memory，第三轮考不住。"""
    def __call__(self, prompt, trajectory, state, memory):
        return {"answer": "抱歉，我不记得"}


def test_good_agent_remembers_context():
    """好 Agent：只建一个 agent，三轮共用 memory，第 3 轮答'北京'。"""
    agent = MemoryAgent(RememberingPlanner())
    for turn in (1, 2, 3):
        res = agent.run(f"第{turn}轮")
    assert turn == 3
    assert "北京" in res["answer"], "好 Agent 应记得北京"


def test_bad_agent_forgets_context():
    """坏 Agent：记忆空、第三轮答'不记得'。"""
    bad = MemoryAgent(ForgettingPlanner())
    for turn in (1, 2, 3):
        bad.run(f"第{turn}轮")
    assert dict(bad.memory.store) == {}, "坏 Agent 记忆应空"


def test_score_context_memory():
    """score_context_memory：好 Agent 1.0，坏 Agent 0.0。"""
    good = MemoryAgent(RememberingPlanner())
    for _ in (1, 2, 3):
        good.run("轮次")
    assert score_context_memory(good, ["user_name"], ["北京"]) == 1.0

    bad = MemoryAgent(ForgettingPlanner())
    for _ in (1, 2, 3):
        bad.run("轮次")
    assert score_context_memory(bad, ["user_name"], ["北京"]) == 0.0
