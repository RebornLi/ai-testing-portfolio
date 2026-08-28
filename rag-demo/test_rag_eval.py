"""D3 检索质量评估测试：Recall@K / Precision@K / MRR / HitRate。

全部离线、可复现：
- 指标数学用"假检索器（已知返回顺序）"精确验证
- 评估引擎用假检索器验证聚合
- 端到端质量门用一个可控的关键词检索器验证召回
不依赖任何模型。
"""
import sys, os
import numpy as np
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "rag"))

from eval_metrics import recall_at_k, precision_at_k, mrr, hit_rate
from eval_engine import evaluate


# ============ 假检索器：已知返回顺序，验证指标数学 ============

class FakeRetriever:
    """返回预设顺序 id 的黑盒检索器。"""
    def __init__(self, order):
        self.order = order  # dict[query] = id 列表

    def retrieve(self, query, k=3):
        ids = self.order.get(query, [])
        return [(i, f"doc-{i}", i * 1.0) for i in ids[:k]]


# ============ 指标数学（用假检索器）============

def test_recall_at_k():
    """① Recall@k = top_k 中命中 golden 比例（分母是 golden 数）。"""
    r = FakeRetriever({"q": [10, 20, 30]})
    hits = [i for i, _, _ in r.retrieve("q", 3)]
    assert recall_at_k(hits, {20}, 1) == 0.0          # top1 是 10，没命中
    assert recall_at_k(hits, {20}, 3) == pytest.approx(1.0)   # 单 golden 命中
    assert recall_at_k(hits, {20, 30}, 3) == pytest.approx(1.0)  # 两个都在 top3
    assert recall_at_k(hits, {20, 30, 99}, 3) == pytest.approx(2 / 3)  # 99 不在


def test_precision_at_k():
    """② Precision@k = top_k 中 golden 占比。"""
    r = FakeRetriever({"q": [10, 20, 30]})
    hits = [i for i, _, _ in r.retrieve("q", 3)]
    assert precision_at_k(hits, {20}, 3) == pytest.approx(1 / 3)
    assert precision_at_k(hits, {20, 30}, 3) == pytest.approx(2 / 3)


def test_mrr():
    """③ MRR = 首个 golden 位置倒数；未命中为 0。"""
    r = FakeRetriever({"q": [10, 20, 30]})
    hits = [i for i, _, _ in r.retrieve("q", 3)]
    assert mrr(hits, {20}) == pytest.approx(1 / 2)     # 位置 2
    assert mrr(hits, {30}) == pytest.approx(1 / 3)     # 位置 3
    assert mrr(hits, {99}) == 0.0                       # 未命中


def test_hit_rate():
    """④ HitRate = 是否至少命中一个 golden（0/1）。"""
    r = FakeRetriever({"q": [10, 20, 30]})
    hits = [i for i, _, _ in r.retrieve("q", 3)]
    assert hit_rate(hits, {20}) == 1.0
    assert hit_rate(hits, {99}) == 0.0


# ============ 评估引擎聚合 ============

def test_evaluate_aggregates():
    """⑤ evaluate() 对多 query 返回均值 + 明细。"""
    r = FakeRetriever({"q1": [5, 1, 2], "q2": [1, 5, 2]})
    golden = [("q1", {1}), ("q2", {1})]
    res = evaluate(r, golden, k=3)
    # 两 query 都命中 golden id=1 且都在 top3
    assert res["mean"]["recall@3"] == pytest.approx(1.0)
    assert res["mean"]["hit_rate"] == pytest.approx(1.0)
    assert len(res["per_query"]) == 2


def test_evaluate_empty_query_set():
    """⑥ 空 golden 集时指标安全归 0，不报错。"""
    r = FakeRetriever({"q": [1, 2]})
    res = evaluate(r, [("q", set())], k=3)
    assert res["mean"]["recall@3"] == 0.0
    assert res["mean"]["precision@3"] == 0.0


# ============ 端到端质量门（可控关键词检索）============

import re


class KeywordRetriever:
    """按关键词重叠度检索，确定性。返回 (id, doc, score)。"""
    def __init__(self, docs):
        self.docs = docs
        self.kw = [set(self._kw(d)) for d in docs]

    @staticmethod
    def _kw(text):
        text = text.lower()
        text = re.sub(r'[。！？；，、,.!?\s]+', ' ', text)
        return set(ch for ch in text if ch.isalnum())

    def retrieve(self, query, k=3):
        qkw = self._kw(query)
        scored = []
        for i, d in enumerate(self.docs):
            overlap = len(qkw & self.kw[i])
            scored.append((i, d, overlap))
        scored.sort(key=lambda x: x[2], reverse=True)
        return scored[:k]


def test_quality_high_recall():
    """⑦ 高质量检索应在 top1 命中相关文档。"""
    docs = [
        "向量数据库存储和检索文本向量表示",
        "今天天气晴朗适合出门散步",
        "RAG 检索增强生成利用外部文档回答问题",
    ]
    r = KeywordRetriever(docs)
    res = evaluate(r, [("什么是向量数据库", {0}),
                        ("RAG 是什么", {2})], k=1)
    assert res["mean"]["hit_rate"] == 1.0
    assert res["mean"]["recall@1"] == 1.0


class ConstantRetriever:
    """永远只返回 id=0 的检索器（命中面极窄）。"""
    def retrieve(self, query, k=3):
        return [(0, "doc-0", 1.0)]


def test_quality_low_recall_flagged():
    """⑧ 低质量检索应被质量门标记（分数低于阈值）。"""
    # 检索器永远只吐出 id=0，但 golden 是 {1}，召回真实为 0
    res = evaluate(ConstantRetriever(), [("q", {1})], k=3)
    assert res["mean"]["recall@3"] < 0.5


def test_quality_threshold_gate():
    """⑨ 质量门：evaluate 暴露分数，调用方可据此卡阈值。"""
    r = ConstantRetriever()  # 永远只吐 id=0
    res = evaluate(r, [("q", {1})], k=3)
    score = res["mean"]["recall@3"]          # 暴露给调用方
    assert 0.0 <= score <= 1.0               # 分数在合法区间
    low = score < 0.5                        # 调用方据此判定质量不合格
    assert bool(low) is True
