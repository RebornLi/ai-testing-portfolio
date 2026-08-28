"""D4：ReAct 全流程（多轮）+ 记忆系统。

D1-D3 测了单轮/多步/协作；D4 往“记忆”走：
    - 记忆写入：agent 把观察结果写进记忆
    - 记忆检索：后续任务能读到已写内容
    - 记忆遗忘：主动删除记忆条目
    - 记忆驱动行为：用了记忆 vs 没用记忆，行为不同
    - 记忆容量：超过容量时（如 LRU / 覆盖）的行为

确定性实现，不依赖真实模型。
"""
import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agentlab"))

from agentlab.tools import invoke_tool
from agentlab.agent import ReActAgent, DeterministicPlanner, Memory, MemoryFull


# ---------- 记忆系统 ----------

def test_memory_write_retrieve():
    """① 写记忆后能检索到对应值。"""
    mem = Memory()
    mem.write("city", "beijing")
    assert mem.retrieve("city") == "beijing"


def test_memory_missing_key_returns_none():
    """② 检索不存在的键 → 返回 None。"""
    mem = Memory()
    assert mem.retrieve("nonexistent") is None


def test_memory_forget():
    """③ 遗忘后键不再存在，检索为 None。"""
    mem = Memory()
    mem.write("k", "v")
    mem.forget("k")
    assert "k" not in mem
    assert mem.retrieve("k") is None


def test_memory_clear():
    """④ clear 后记忆为空。"""
    mem = Memory()
    mem.write("a", 1)
    mem.write("b", 2)
    mem.clear()
    assert len(mem) == 0


def test_memory_capacity_overflow():
    """⑤ 超过容量上限写新键 → 抛 MemoryFull（容量有上限）。"""
    mem = Memory(capacity=2)
    mem.write("a", 1)
    mem.write("b", 2)
    with pytest.raises(MemoryFull):
        mem.write("c", 3)


# ---------- ReAct 全流程 + 记忆 ----------

def test_full_flow_retrieve_from_memory():
    """⑥ agent 用记忆检索到之前写入的内容。"""
    mem = Memory()
    mem.write("answer_to_3_plus_4", "7")

    class MemoryPlanner:
        """第二轮检索记忆，返回记忆中的值当答案。"""
        round = 0

        def __call__(self, history, state):
            self.round += 1
            if self.round == 1:
                return {"tool": ("add", {"a": 3, "b": 4})}
            # 第二轮从记忆取答案
            assert "answer_to_3_plus_4" in mem
            return {"answer": mem.retrieve("answer_to_3_plus_4")}

    agent = ReActAgent(MemoryPlanner(), max_iterations=10)
    res = agent.run("3+4")
    assert res["answer"] == "7"
    assert len(res["trajectory"]) == 1


def test_memory_drives_behavior():
    """⑦ 有记忆 vs 无记忆，agent 行为不同。"""
    # 有记忆：第二轮从记忆取到值
    mem = Memory()
    mem.write("cached", "hello")

    class WithMemPlanner:
        round = 0

        def __call__(self, history, state):
            self.round += 1
            if self.round == 1:
                return {"tool": ("lookup", {"city": "shanghai"})}
            return {"answer": mem.retrieve("cached")}

    res = ReActAgent(WithMemPlanner(), max_iterations=10).run("有记忆")
    assert res["answer"] == "hello"

    # 无记忆：第二轮检索到 None
    class NoMemPlanner:
        round = 0

        def __call__(self, history, state):
            self.round += 1
            if self.round == 1:
                return {"tool": ("lookup", {"city": "shanghai"})}
            return {"answer": Memory().retrieve("cached")}

    res2 = ReActAgent(NoMemPlanner(), max_iterations=10).run("无记忆")
    assert res2["answer"] is None


# ---------- 多轮记忆写入----------

def test_memory_writes_during_run():
    """⑧ agent 运行中可把中间结果写进记忆。"""
    mem = Memory()

    class WriteThenAnswerPlanner:
        round = 0

        def __call__(self, history, state):
            self.round += 1
            if self.round == 1:
                return {"tool": ("add", {"a": 10, "b": 5})}
            # 第二步把结果 15 写进记忆
            mem.write("intermediate", 15)
            assert mem.retrieve("intermediate") == 15
            return {"answer": "written"}

    agent = ReActAgent(WriteThenAnswerPlanner(), max_iterations=10)
    res = agent.run("写记忆")
    assert mem.retrieve("intermediate") == 15
    assert res["answer"] == "written"


def test_full_flow_trajectory_complete():
    """⑨ 多轮全流程：轨迹非空 + 有答案 + 终止正常。"""
    agent = ReActAgent(
        DeterministicPlanner([
            ("tool", "add", {"a": 2, "b": 3}),
            ("tool", "lookup", {"city": "beijing"}),
            ("answer", "done"),
        ]),
        max_iterations=10,
    )
    res = agent.run("多轮任务")
    assert len(res["trajectory"]) == 2
    assert res["answer"] == "done"
    assert res["reason"] == "stopped"


def test_memory_capacity_allows_up_to_limit():
    """⑩ 容量为 N 时最多能写 N 个不重复键。"""
    mem = Memory(capacity=3)
    for i in range(3):
        mem.write(f"k{i}", i)
    assert len(mem) == 3
    with pytest.raises(MemoryFull):
        mem.write("k3", 3)
