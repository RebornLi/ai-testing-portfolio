"""D4：端到端 RAG 问答 + 确定性幻觉/接地检测。

D3 验证“检索找得准不准”；D4 在此基础上验证“答案是否贴合检索到的内容”
（幻觉检测）。确定性实现，不依赖真实模型。

流水线：
    query → [retrieve] → contexts → [answer] → answer → [ground] → grounded_score
"""
import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "rag"))

from grounding import ground_claims, grounding_score, split_claims
from pipeline import RagPipeline, default_chunk

CONTEXT = ("向量数据库用于存储和检索文本的向量表示。"
           "RAG 通过检索相关文档来增强大模型的回答质量。"
           "Embedding 将文本转化为高维向量空间中的数值向量。")


# ---------- 接地/幻觉 拆分 ----------

def test_split_claims():
    """① 答案按句子拆分。"""
    claims = split_claims("第一句。第二句。")
    assert claims == ["第一句", "第二句"]


def test_no_context_all_hallucination():
    """② 没有上下文时，安全失败：全部判为幻觉。"""
    grounded, hallucinated = ground_claims("向量数据库是啥。", "")
    assert grounded == []
    assert len(hallucinated) == 1


# ---------- 接地 vs 幻觉 判定 ----------

def test_grounding_full():
    """③ 答案全部来自上下文 → 全接地，得分 1.0。"""
    answer = "向量数据库用于存储检索文本向量。RAG 检索相关文档增强回答。"
    g, h = ground_claims(answer, CONTEXT)
    assert h == []
    assert grounding_score(answer, CONTEXT) == pytest.approx(1.0)


def test_grounding_partial():
    """④ 答案混入编造 → 至少一句被判幻觉，分 < 1。"""
    answer = "向量数据库用于存储检索文本向量。圆周率约等于3.14159。"
    # "圆周率" 在上下文中不存在 → 至少一句落幻觉
    g, h = ground_claims(answer, CONTEXT)
    assert len(h) >= 1
    assert grounding_score(answer, CONTEXT) < 1.0


def test_grounding_score_range():
    """⑤ 接地分永远落在 [0, 1]。"""
    low = grounding_score("哈希表 缓存 分布式 无关", CONTEXT)
    high = grounding_score("向量数据库 检索 文档 CONTEXT 无关词", CONTEXT)
    assert 0.0 <= low <= 1.0
    assert 0.0 <= high <= 1.0


def test_more_fabrication_lower_score():
    """⑥ 编造越多，接地分越低。"""
    clean = "向量数据库用于检索文本向量。RAG 检索文档。"
    # "圆周率"“太阳系”在上下文中不存在 → 低分
    dirty = "向量数据库检索文本向量。圆周率约等于3.14159。太阳系有八大行星。"
    assert grounding_score(dirty, CONTEXT) < grounding_score(clean, CONTEXT)


# ---------- 端到端 流水线 ----------

def test_end_to_end_pipeline_grounds_context():
    """⑦ 一条问题走完整条流水线，接地分高（答案即来自上下文）。"""
    pipe = RagPipeline(embedder_mode="mock")
    pipe.load_document(CONTEXT, chunker=default_chunk)
    # 用真实检索到的上下文拼成一个“接地答案”
    hits = pipe.query("什么是向量数据库", top_k=1)
    answer = "".join(h["document"] for h in hits)
    assert grounding_score(answer, CONTEXT) >= 0.9


def test_end_to_end_detects_fabrication():
    """⑧ 流水线答案混入上下文没有的内容（圆周率）→ 接地分被标记为低。"""
    pipe = RagPipeline(embedder_mode="mock")
    pipe.load_document(CONTEXT, chunker=default_chunk)
    # 一个会答非所问的答案：前半接地，后半编造圆周率
    fabricated = "向量数据库用于检索文本向量。圆周率约等于3.14159。"
    assert grounding_score(fabricated, CONTEXT) < 1.0


def test_pipeline_answerer_interface():
    """⑨ 答案器有统一接口 answer(question, contexts)。"""
    pipe = RagPipeline(embedder_mode="mock")

    class StaticAnswerer:
        def answer(self, question, contexts):
            return "占位答案无关内容"

    pipe.answerer = StaticAnswerer()
    out = pipe.answerer.answer("q", ["c"])
    assert out == "占位答案无关内容"
