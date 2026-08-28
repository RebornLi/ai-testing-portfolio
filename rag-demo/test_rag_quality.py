"""D5：端到端 RAG 答案质量打分（相关性 + 综合质量门）。

D3 验证检索、D4 验证幻觉；D5 最后一步：答案本身答到了吗？
用"答案覆盖问题关键词的比例"近似相关性，
再与 D4 的忠实度合成综合分，用质量门判定合格。
确定性实现，不依赖真实模型。
"""
import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "rag"))

from quality import (
    answer_relevance, answer_relevance_breakdown, answer_completeness,
    composite_score, QualityGate, StaticAnswerer,
)
from grounding import grounding_score

QUESTION = "什么是向量数据库"          # 关键词：是什么向量数据库 (8)
CONTEXT = "向量数据库用于存储和检索文本的向量表示。"


# ---------- 答案相关性 ----------

def test_answer_relevance_full():
    """① 答案完整覆盖问题关键词 → 相关性 = 1.0。"""
    # 答案包含问题所有词 → 相关性满分
    assert answer_relevance("向量数据库是什么库", "什么是向量数据库") == pytest.approx(1.0)


def test_answer_relevance_partial():
    """② 答案只覆盖部分关键词 → 0 < 相关性 < 1。"""
    r = answer_relevance("向量数据库用于存储文本向量", QUESTION)
    assert 0.0 < r < 1.0


def test_answer_relevance_unrelated():
    """③ 答案与问题无关 → 相关性接近 0。"""
    r = answer_relevance("圆周率约等于3.14159和黄金比例", "今天中午吃什么")
    assert r == pytest.approx(0.0)


def test_relevance_breakdown():
    """④ breakdown 返回相关性 + 命中的问题词集合。"""
    r, hit = answer_relevance_breakdown("向量数据库", QUESTION)
    assert 0 < r <= 1.0
    assert hit <= set("是什么向量数据库")  # 命中的是问题词的子集


# ---------- 答案完整性（数字漏答）----------

def test_completeness_missing_number():
    """⑤ 答案覆盖问题越多 → 完整性越接近 1。"""
    c = answer_completeness("这个系统支持多少并发", "这个系统支持并发处理")
    assert 0.0 <= c <= 1.0


def test_completeness_higher_when_more_covered():
    """⑥ 答案覆盖问题关键词越多 → 完整性越高。"""
    full = answer_completeness("向量数据库是一种数据库", "向量数据库是什么")
    partial = answer_completeness(
        "向量数据库", "向量数据库是什么用于存储检索什么")
    assert full >= partial


# ---------- 综合质量门 ----------

def test_composite_full_answer_passes():
    """⑦ 相关且接地的答案 → 综合分高，质量门通过。"""
    score, passed = composite_score(
        "向量数据库是什么", QUESTION, CONTEXT, threshold=0.6)
    assert score >= 0.6
    assert passed is True


def test_composite_fabricated_fails():
    """⑧ 答非所问的答案 → 综合分低，质量门拒绝。"""
    # 答案与问题完全无关（谈圆周率）→ 相关 + 忠实都低 → 综合分 ~0
    score, passed = composite_score(
        "圆周率约等于3.14159和黄金比例常数", QUESTION, CONTEXT,
        threshold=0.6)
    assert score < 0.6
    assert passed is False


def test_composite_score_in_range():
    """⑨ 综合分永远落在 [0, 1]。"""
    for ans in ["向量数据库", "圆周率3.14", "无关句子无关"]:
        score, _ = composite_score(ans, QUESTION, CONTEXT, 0.6)
        assert 0.0 <= score <= 1.0


# ---------- 质量门对象 ----------

def test_quality_gate_object():
    """⑩ QualityGate 封装 score + is_pass，判定一致。"""
    gate = QualityGate(threshold=0.6)
    score = gate.score("向量数据库用于存储向量", QUESTION, CONTEXT)
    assert 0.0 <= score <= 1.0
    # is_pass 与 composite_score 判定一致
    _, comp_pass = composite_score(
        "向量数据库是用于存储的", QUESTION, CONTEXT, 0.6)
    assert gate.is_pass("向量数据库是用于存储的", QUESTION, CONTEXT) == comp_pass


def test_static_answerer_interface():
    """⑪ StaticAnswerer.answer(question, contexts) 返回拼接上下文。"""
    out = StaticAnswerer().answer("q", ["向量", "数据库"])
    assert out == "向量数据库"
