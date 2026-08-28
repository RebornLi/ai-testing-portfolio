"""D5 DeepEval 自动化评测测试（确定性 metric，不依赖 key）。

复刻 DeepEval 链路：TestCase → Metric → evaluate。
关键坑：自己写的确定性 metric 必须实现 measure/successful（async a_measure
在真实 deepeval 里要 async 版；这里用离线封装 run_deep_eval 复刻该链路）。
"""
import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "evalagents"))

from evalagents.metrics import (KeywordMetric, run_deep_eval, make_llm_test_case,
                     score_integration)


def test_keyword_metric_hit():
    """命中关键词 → score=1.0, success=True。"""
    m = KeywordMetric(keyword="北京")
    tc = make_llm_test_case("我喜欢哪个城市", "我喜欢北京")
    assert m.evaluate(tc) == 1.0
    assert m.successful()


def test_keyword_metric_miss():
    """未命中 → score=0.0, success=False。"""
    m = KeywordMetric(keyword="北京")
    tc = make_llm_test_case("我喜欢哪个城市", "我不确定")
    assert m.evaluate(tc) == 0.0
    assert not m.successful()


def test_run_deep_eval_pass_rate():
    """跑一组：命中 + 未命中 → 整体 50%。"""
    tc_ok = make_llm_test_case("我喜欢哪个城市", "我喜欢北京")
    tc_bad = make_llm_test_case("我喜欢哪个城市", "我不确定")
    res = run_deep_eval([tc_ok, tc_bad], KeywordMetric(keyword="北京"))
    assert res["pass_rate"] == 0.5


def test_deep_eval_no_success_attr_like_real():
    """复刻 W6-D5 踩坑：evaluate 返回的是结果集，没有 .success 属性。
    整体通过率要自己算（通过的条数 / 总条数）。
    """
    tc = make_llm_test_case("我喜欢哪个城市", "我喜欢北京")
    res = run_deep_eval([tc], KeywordMetric(keyword="北京"))
    # 真实 deepeval 的 evaluate() 没有 .success —— 这里我们读 .pass_rate
    assert res["pass_rate"] == 1.0


def test_integration_full_score():
    """D6 整合：好 Agent 四维度全 1.0，总分 1.0。"""
    # 工具 1.0、完成率 1.0、上下文 1.0、成本 1.0
    assert score_integration(1.0, 1.0, 1.0, 1.0) == 1.0
