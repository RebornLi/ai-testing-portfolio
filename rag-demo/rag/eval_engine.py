"""eval_engine.py — 用 golden 集评估检索质量。

检索器是个黑盒：给定 query 返回 [(id, doc, score), ...]。
我们把返回结果和"应命中的 golden id"对比，算出 Recall@K / Precision@K /
MRR / HitRate，再在多个 query 上取平均。

认知边界：
- golden 来源可以是人工标注，也可以用"文档关键词 overlap"近似（离线）。
- RAGAS 的 faithfulness/answer-relevance 需要真实 embedding 或 LLM judge，
  这里不覆盖，留到 D5。
"""
import numpy as np
from eval_metrics import recall_at_k, precision_at_k, mrr, hit_rate


def evaluate(retriever, golden_queries, k=3):
    """对每个 (query, golden_ids) 算检索指标，返回均值 + 每_query 明细。

    retriever: 带 .retrieve(query, k) -> [(id, doc, score), ...] 的对象。
    golden_queries: list[(query, set(golden_ids))]
    """
    per = []
    for query, golden in golden_queries:
        hits = [i for i, _, _ in retriever.retrieve(query, k)]
        rec = recall_at_k(hits, golden, k)
        pre = precision_at_k(hits, golden, k)
        m = mrr(hits, golden)
        hr = hit_rate(hits, golden)
        per.append({"query": query, "recall@%d" % k: rec,
                    "precision@%d" % k: pre, "mrr": m, "hit_rate": hr})
    n = len(per) or 1
    mean = {
        "recall@%d" % k: np.mean([p["recall@%d" % k] for p in per]),
        "precision@%d" % k: np.mean([p["precision@%d" % k] for p in per]),
        "mrr": np.mean([p["mrr"] for p in per]),
        "hit_rate": np.mean([p["hit_rate"] for p in per]),
    }
    return {"mean": mean, "per_query": per}
