"""测试维度4：DeepEval 离线确定性兜底（无需 key）。

指标 API：score() 返回 (score, passed, errors) 三元组（errors=未达标原因列表）。
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from metrics import DeepEvalMetric, evaluate_dimensions


def test_deepeval_keyword_hit():
    """命中关键词 → 通过。"""
    m = DeepEvalMetric(actual="我喜欢北京", expected="北京", keyword="北京")
    score, passed, errors = m.score()
    assert passed and score == 1.0
    assert errors == []


def test_deepeval_keyword_miss():
    """未命中关键词 → 不通过。"""
    m = DeepEvalMetric(actual="我不确定", expected="北京", keyword="北京")
    score, passed, errors = m.score()
    assert not passed and score == 0.0
    assert any("命中" in e for e in errors)


def test_deepeval_exact_match():
    """无关键词兜底：精确匹配。"""
    m = DeepEvalMetric(actual="北京", expected="北京")
    score, passed, _ = m.score()
    assert passed
    m2 = DeepEvalMetric(actual="上海", expected="北京")
    score2, passed2, _ = m2.score()
    assert not passed2
