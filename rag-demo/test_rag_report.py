"""D6：端到端 RAG 评估报告 + 质量汇总。

D1~D5 分别测了检索、幻觉、答案质量；D6 把它们串成一份端到端报告：
对一批 query 跑“检索→答案→评分→质量门”，汇总平均相关性/忠实度/综合分/
通过率，并支持质量门判定与报告格式化。

确定性实现，不依赖真实模型。
"""
import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "rag"))

from pipeline import RagPipeline, default_chunk
from quality import StaticAnswerer
from report import RagEvaluator, report_text

DOC = ("向量数据库用于存储和检索文本的向量表示。"
       "RAG 通过检索相关文档来增强大模型的回答质量。"
       "Embedding 将文本转化为高维向量空间中的数值向量。"
       "余弦相似度用于衡量两个文本向量之间的相似程度。"
       "分块策略影响检索的准确性和速度表现。")


@pytest.fixture
def pipeline():
    pipe = RagPipeline(embedder_mode="mock")
    pipe.load_document(DOC, chunker=default_chunk)
    return pipe


def make_golden(questions):
    """构造 (query, context) 集：context 统一用 DOC。"""
    return [(q, DOC) for q in questions]


# ---------- 空边界 ----------

def test_evaluate_empty_golden(pipeline):
    """① 空 golden 集：rows 为空，汇总 total=1（安全，不除零）。"""
    ev = RagEvaluator(pipeline, StaticAnswerer())
    res = ev.evaluate([])
    assert res["rows"] == []
    assert res["summary"]["total"] == 1
    assert 0.0 <= res["summary"]["avg_score"] <= 1.0


# ---------- 单条质量 ----------

def test_single_query_reports(pipeline):
    """② 单条 query：汇总 total=1，有 1 行明细。"""
    ev = RagEvaluator(pipeline, StaticAnswerer())
    res = ev.evaluate(make_golden(["什么是向量数据库"]))
    assert res["summary"]["total"] == 1
    assert len(res["rows"]) == 1
    row = res["rows"][0]
    assert row["query"] == "什么是向量数据库"
    assert 0.0 <= row["relevance"] <= 1.0
    assert 0.0 <= row["faithfulness"] <= 1.0


# ---------- 端到端质量门判定 ----------

class FullStaticAnswerer(StaticAnswerer):
    """全静态答案器：答案即拼接到的上下文（最朴素答案）。"""


def test_high_quality_passes_gate(pipeline):
    """③ 答案贴合上下文 → 综合分高，过质量门。"""
    ev = RagEvaluator(pipeline, StaticAnswerer(), threshold=0.6)
    res = ev.evaluate(make_golden(["什么是向量数据库", "RAG 的作用"]))
    assert res["summary"]["pass_rate"] == 1.0
    assert res["summary"]["avg_score"] >= 0.6


class FabricatingAnswerer:
    """编造答案的答案器：答案全是上下文没有的内容。"""

    def answer(self, question, contexts):
        return "圆周率约等于3.14159黄金比例常数无关内容"


def test_fabrication_fails_gate(pipeline):
    """④ 答案编造上下文外内容 → 综合分低，质量门拒绝。"""
    ev = RagEvaluator(pipeline, FabricatingAnswerer(), threshold=0.6)
    res = ev.evaluate(make_golden(["什么是向量数据库"]))
    assert res["summary"]["pass_rate"] == 0.0
    assert res["summary"]["avg_score"] < 0.5


def test_pass_rate_counts_passed():
    """⑤ pass_rate = 通过数 / 总数（用假评估器验证聚合）。"""

    class FakePipeline:
        def query(self, q, top_k=2):
            return [{"document": "向量数据库上下文", "score": 1.0}]

    class TwoAnswerer:
        """第一条答得贴合，第二条答非所问。"""
        def answer(self, question, contexts):
            if "向量" in question:
                return "向量数据库用于存储检索文本向量表示"
            return "圆周率黄金比例常数无关内容"

    ev = RagEvaluator(FakePipeline(), TwoAnswerer(), threshold=0.6)
    res = ev.evaluate(make_golden(
        ["什么是向量数据库", "圆周率是什么"]))
    # 第一条过、第二条不过 → 通过率 0.5
    assert res["summary"]["pass_rate"] == 0.5


# ---------- 汇总指标 ----------

def test_summary_metrics_in_range():
    """⑥ 所有汇总指标落在 [0, 1]。"""

    class FakePipeline:
        def query(self, q, top_k=2):
            return [{"document": DOC, "score": 1.0}]

    ev = RagEvaluator(FakePipeline(), StaticAnswerer())
    res = ev.evaluate(make_golden(
        ["什么是向量数据库", "RAG 作用", "余弦相似度"]))
    for key in ("avg_relevance", "avg_faithfulness", "avg_score", "pass_rate"):
        assert 0.0 <= res["summary"][key] <= 1.0


# ---------- 阈值敏感性 ----------

def test_higher_threshold_stricter(pipeline):
    """⑦ 阈值越高 → 通过率越低或持平（不会升高）。"""
    low = RagEvaluator(pipeline, StaticAnswerer(), threshold=0.5)
    high = RagEvaluator(pipeline, StaticAnswerer(), threshold=0.8)
    rows = make_golden(["什么是向量数据库", "RAG 作用", "余弦相似度"])
    assert high.evaluate(rows)["summary"]["pass_rate"] <= \
        low.evaluate(rows)["summary"]["pass_rate"]


# ---------- 报告格式化 ----------

def test_report_text_contains_summary(pipeline):
    """⑧ 报告文本包含平均分和每个 query。"""
    ev = RagEvaluator(pipeline, StaticAnswerer())
    res = ev.evaluate(make_golden(["什么是向量数据库", "RAG 作用"]))
    report = report_text(res)
    assert "评估报告" in report
    assert "什么是向量数据库" in report
    assert "RAG 作用" in report
    assert "综合平均分" in report


def test_report_text_contains_quality_marks(pipeline):
    """⑨ 报告里合格的 query 带标记（✅ / ❌）。"""
    ev = RagEvaluator(pipeline, StaticAnswerer())
    res = ev.evaluate(make_golden(["什么是向量数据库"]))
    report = report_text(res)
    assert "✅" in report or "❌" in report
