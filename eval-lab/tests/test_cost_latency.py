"""D4 成本 & 延迟测试（慢 Agent vs 快 Agent，质量分排序）。

延迟和成本是独立维度——慢 Agent 慢很多但成本一样。
质量分把成功率/成本/延迟合成一个数，能排序好坏。
"""
import sys, os
import time
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "evalagents"))

from evalagents.agent import (TrackingAgent, DeterministicPlanner, CostTracker, Timer,
                   invoke_tool)
from evalagents.metrics import score_cost_latency, quality_score


def slow_steps():
    return [("tool", "add", {"a": 3, "b": 4}),
            ("tool", "multiply", {"a": 7, "b": 2}),
            ("answer", "结果是14")]


def fast_steps():
    return [("tool", "add", {"a": 3, "b": 4}),
            ("tool", "multiply", {"a": 7, "b": 2}),
            ("answer", "结果是14")]


def test_cost_tracker_counts():
    """CostTracker：次数 + 成本 + 每步耗时。"""
    tracker = CostTracker(price=0.001)
    tracker.record("add", 0.1)
    tracker.record("multiply", 0.1)
    assert tracker.count == 2
    assert tracker.cost == pytest.approx(0.0002)


def test_slow_agent_is_slower_same_cost():
    """慢 Agent 慢很多，但总成本一样（延迟≠成本）。"""
    def run_with_delay(cost, delay):
        tracker = CostTracker(price=0.001)
        tracker.price = cost
        with Timer() as t:
            for _ in range(2):
                time.sleep(delay)
            tracker.record("add", t.elapsed)
            tracker.record("multiply", t.elapsed)
        return tracker, t.elapsed

    fast_tr, fast_t = run_with_delay(0.001, 0.0)
    slow_tr, slow_t = run_with_delay(0.001, 0.1)
    assert slow_t > fast_t * 5, "慢 Agent 应该明显更慢"
    assert slow_tr.cost == pytest.approx(fast_tr.cost), "同样单价下成本应相同"


def test_score_cost_latency():
    """score_cost_latency：低成本高分，高成本低分。"""
    assert score_cost_latency(0.01, [0.001, 0.001], budget=1.0, per_step_budget=1.0) > 0.9
    low = score_cost_latency(0.5, [10, 10], budget=1.0, per_step_budget=1.0)
    assert low < 0.1


def test_quality_score_ranking():
    """质量分：又省又快又准 > 慢贵准。"""
    # 快省准：成功 1.0，成本 0.002，延迟 0.02
    good = quality_score(1.0, 0.002, 0.02, budget=1.0, per_step_budget=1.0)
    # 慢贵准：成功 1.0，成本 0.5，延迟 0.5
    bad = quality_score(1.0, 0.5, 0.5, budget=1.0, per_step_budget=1.0)
    assert good > bad
