"""D2 集成测试：embedder + store 串起来，验证检索链路。

全部使用 MockEmbedder/MockVectorStore —— 不依赖真实模型/服务/网络。
"""
import sys, os
import numpy as np
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "rag"))

from embedders import MockEmbedder, get_embedder
from store import MockVectorStore, get_store
from pipeline import RagPipeline, default_chunk

DOC = ("向量数据库用于存储和检索文本的向量表示。"
       "RAG通过检索相关文档来增强大模型的回答质量。"
       "Embedding将文本转化为高维向量空间中的数值向量。"
       "余弦相似度用于衡量两个文本向量之间的相似程度。"
       "分块策略影响检索的准确性和系统速度表现。")


# ---------- MockEmbedder 独立测试 ----------

def test_mock_embedder_has_fixed_dim():
    """① 嵌入维度固定 32。"""
    assert MockEmbedder().embed("hello").shape == (32,)


def test_mock_embedder_normalizes():
    """② 嵌入已归一化（模=1）。"""
    v = MockEmbedder().embed("abc")
    assert float(v @ v) == pytest.approx(1.0, abs=1e-5)


def test_mock_embedder_same_text_same_vec():
    """③ 确定性：同文本返回同向量。"""
    a = MockEmbedder().embed("稳定")
    b = MockEmbedder().embed("稳定")
    assert np.allclose(a, b)


# ---------- get_embedder 工厂 ----------

def test_factory_returns_mock_instance():
    """④ 工厂 mock 模式返回 MockEmbedder 实例。"""
    from embedders import MockEmbedder
    assert isinstance(get_embedder(mode="mock"), MockEmbedder)


# ---------- MockVectorStore 独立测试 ----------

def test_store_empty_search_returns_empty():
    """⑤ 空库搜索返回空列表。"""
    store = MockVectorStore(dim=32)
    assert store.search([0.1] * 32, top_k=3) == []


def test_store_search_ranks_by_similarity():
    """⑥ 最相似的向量排在最前。"""
    store = MockVectorStore(dim=4)
    v1 = np.array([1.0, 0.0, 0.0, 0.0])
    v2 = np.array([0.0, 1.0, 0.0, 0.0])
    store.add(v1, "文档A")
    store.add(v2, "文档B")
    q = np.array([1.0, 0.0, 0.0, 0.0])  # 与文档A完全一致
    hits = store.search(q, top_k=2)
    assert hits[0]["document"] == "文档A"
    assert hits[1]["document"] == "文档B"


# ---------- 集成链路 ----------

def test_pipeline_load_and_query():
    """⑦ 一条文档入库，查询命中含相关词的块。"""
    pipe = RagPipeline(embedder_mode="mock", store_mode="mock")
    pipe.load_document(DOC, chunker=default_chunk)
    assert len(pipe.store) >= 1
    hits = pipe.query("什么是向量数据库", top_k=1)
    assert len(hits) == 1
    assert "向量" in hits[0]["document"] or "检索" in hits[0]["document"]


def test_pipeline_retrieval_consistency():
    """⑧ 确定性管线：同查询两次返回同结果。"""
    pipe = RagPipeline()
    pipe.load_document(DOC, chunker=default_chunk)
    a = pipe.query("向量数据库存什么", top_k=1)[0]["document"]
    b = pipe.query("什么是向量数据库", top_k=1)[0]["document"]
    assert a == b


def test_factory_store_returns_mock():
    """⑨ 工厂 mock 模式返回 MockVectorStore。"""
    from store import MockVectorStore
    assert isinstance(get_store(mode="mock", dim=32), MockVectorStore)
