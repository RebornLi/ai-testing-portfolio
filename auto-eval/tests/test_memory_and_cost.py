"""测试维度2（记忆）+ 维度3（成本/延迟）。

指标 API：score() 返回 (score, passed, errors) 三元组。
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from autoeval.agent import Memory, MemoryAgent
from autoeval.metrics import MemoryMetric, CostLatencyMetric


class RememberingPlanner:
    """记住关键信息供后续轮读取。"""
    turn = 1
    def __call__(self, prompt, memory, maxit):
        if self.turn == 1:
            memory.write("name", "小明")
            memory.write("city", "北京")
            self.turn += 1
            return {"answer": "记下"}
        city = memory.read("city")
        self.turn += 1
        return {"answer": f"你喜欢{city}" if city else "忘了"}


class ForgettingPlanner:
    """不写记忆，必然失忆。"""
    turn = 1
    def __call__(self, prompt, memory, maxit):
        self.turn += 1
        return {"answer": "我不知道"}


def test_memory_good():
    """好 agent 记住城市，同一个 agent 跨轮能读到（记忆跨轮存活）。"""
    mem = Memory()
    planner = RememberingPlanner()
    MemoryAgent(mem, planner).run("第1轮")   # 写记忆：name + city
    MemoryAgent(mem, planner).run("第2轮")   # 读到 city
    assert MemoryAgent(mem, planner).run("第3轮")["answer"] == "你喜欢北京"
    score, passed, errors = MemoryMetric(mem, {"name": "小明", "city": "北京"}).score()
    assert passed and score == 1.0, (score, passed)
    assert errors == []


def test_memory_bad_fails():
    """坏 agent 不写记忆 → 失忆。"""
    mem = Memory()
    MemoryAgent(mem, ForgettingPlanner()).run("第1轮")
    score, passed, errors = MemoryMetric(mem, {"name": "小明"}).score()
    assert not passed and score == 0.0
    assert any("忘记" in e for e in errors)


def test_cost_latency_good():
    """成本延迟都在预算内。"""
    m = CostLatencyMetric(cost=0.5, latency=1.0)
    score, passed, _ = m.score()
    assert passed and score == 1.0


def test_cost_latency_bad():
    """成本超预算 → 不达标。"""
    m = CostLatencyMetric(cost=2.0, latency=1.0, cost_budget=1.0)
    score, passed, errors = m.score()
    assert not passed
    assert any("成本" in e for e in errors)


def test_latency_realistic():
    """真实计时：sleep 0.05s 应在预算内。"""
    with open(os.path.join(os.path.dirname(__file__), "..", "autoeval", "tools.py")):
        pass
    t0 = time.time()
    time.sleep(0.05)
    lat = time.time() - t0
    m = CostLatencyMetric(cost=0.01, latency=lat, latency_budget=5.0)
    score, passed, _ = m.score()
    assert passed
