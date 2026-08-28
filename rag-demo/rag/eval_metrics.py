"""eval_metrics.py — RAG 检索质量评估指标。

只算"检索层"质量：给定问题，真实应命中的文档（golden）是否出现在
top_k 里。所有分数 0~1。不依赖真实模型——只要有一个"是否相关"的判断
来源（golden 答案 / 标注）就能算。

认知边界：RAGAS 那套（faithfulness、answer relevance、precision/recall）
需要真实 embedding 或 LLM judge；这里只做"检索命中"这一维的确定性指标，
用 keyword-overlap 作为 golden 的等价替身，离线可跑。
"""
import numpy as np


def _keywords(text):
    """极简关键词提取：去中文标点 + 按字/词切。教学用。"""
    import re
    text = text.lower()
    text = re.sub(r'[。！？；，、,.!?\s]+', ' ', text)
    return set(text.replace(' ', '')) if text else set()


def recall_at_k(hits, golden_ids, k):
    """Recall@k = top_k 中命中 golden 的比例。
    hits: 检索返回的 id 列表
    golden_ids: 应命中的真实 id 列表
    """
    top = hits[:k]
    hit = [i for i in top if i in set(golden_ids)]
    if not golden_ids:
        return 0.0
    return len(hit) / len(golden_ids)


def precision_at_k(hits, golden_ids, k):
    """Precision@k = top_k 中 golden 占比。"""
    top = hits[:k]
    hit = [i for i in top if i in set(golden_ids)]
    if not top:
        return 0.0
    return len(hit) / len(top)


def mrr(hits, golden_ids):
    """Mean Reciprocal Rank：首个 golden 出现位置的倒数。
    没命中 → 0。只接受单 golden 场景，所以是 RR（不是 MRR）。
    """
    for i, h in enumerate(hits):
        if h in set(golden_ids):
            return 1.0 / (i + 1)
    return 0.0


def hit_rate(hits, golden_ids):
    """Hit Rate = top_k 里是否"至少命中一个 golden"。0/1。"""
    return 1.0 if any(i in set(golden_ids) for i in hits) else 0.0
