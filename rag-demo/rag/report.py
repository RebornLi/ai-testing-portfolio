"""report.py — RAG 端到端评估报告。

把 D1~D5 的三条线串成一份报告：
    query → [检索] → contexts → [答案器] → answer
            → [相关性] + [接地/幻觉] → composite → 质量门判定

评估器是黑盒：任何带 .query(question, top_k) 的检索器，
加上任意 .answer(question, contexts) 的答案器，都能跑。

认知边界：
    相关性 / 接地用确定性关键词重叠近似（离线可复现）。
    真实系统应换 embedding 语义相似度 + LLM-as-Judge。
"""
import numpy as np

from quality import answer_relevance, composite_score, answer_completeness
from grounding import grounding_score, split_claims


class RagEvaluator:
    """端到端评估器：跑一批 query，汇总指标。"""

    def __init__(self, pipeline, answerer, threshold=0.6):
        """pipeline: 带 .query(question, top_k) 的管线。
        answerer: 带 .answer(question, contexts) 的答案器。
        """
        self.pipeline = pipeline
        self.answerer = answerer
        self.threshold = threshold

    def evaluate(self, golden, top_k=2):
        """对每条 (query, context) 打分，返回 {"summary", "rows"}。

        golden: list[(query, context)]
        每条返回 relevance / faithfulness / score / passed / 明细。
        """
        rows = []
        for query, context in golden:
            hits = self.pipeline.query(query, top_k=top_k)
            contexts = [h["document"] for h in hits]
            answer = self.answerer.answer(query, contexts)

            rel = answer_relevance(answer, query)
            faith = grounding_score(answer, context)
            score, passed = composite_score(answer, query, context,
                                            self.threshold)
            rows.append({
                "query": query,
                "relevance": round(rel, 4),
                "faithfulness": round(faith, 4),
                "score": round(score, 4),
                "passed": passed,
                "contexts_hit": len(hits),
            })

        n = len(rows) or 1
        def _mean(values):
            values = list(values)
            return round(float(np.mean(values)), 4) if values else 0.0
        summary = {
            "total": n,
            "avg_relevance": _mean([r["relevance"] for r in rows]),
            "avg_faithfulness": _mean([r["faithfulness"] for r in rows]),
            "avg_score": _mean([r["score"] for r in rows]),
            "pass_rate": _mean([1.0 if r["passed"] else 0.0 for r in rows]),
        }
        return {"summary": summary, "rows": rows}

    @staticmethod
    def summary_report(evaluation):
        """把评估结果格式化成人类可读的报告字符串。"""
        s = evaluation["summary"]
        lines = [
            "=" * 48,
            "RAG 端到端评估报告",
            "=" * 48,
            f"评测问题数 : {s['total']}",
            f"平均相关性 : {s['avg_relevance']:.3f}",
            f"平均忠实度 : {s['avg_faithfulness']:.3f}",
            f"综合平均分 : {s['avg_score']:.3f}",
            f"质量通过率 : {s['pass_rate']:.3f}",
            "-" * 48,
        ]
        for r in evaluation["rows"]:
            mark = "✅" if r["passed"] else "❌"
            lines.append(
                f"{mark} [{r['relevance']:.2f}/{r['faithfulness']:.2f}] "
                f"{r['query']}"
            )
        lines.append("=" * 48)
        return "\n".join(lines)


def report_text(evaluation):
    """快捷函数：把评估结果转成报告文本。"""
    return RagEvaluator.summary_report(evaluation)
