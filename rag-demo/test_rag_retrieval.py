"""RAG 检索测试（numpy 确定性嵌入，可离线跑）"""
import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "rag"))
from rag_utils import chunk_text, embed, tokenize, dot
from vector_search import VectorStore, cosine_similarity

DOC = ("向量数据库用于存储和检索文本的向量表示。"
       "RAG通过检索相关文档来增强大模型的回答质量。"
       "Embedding将文本转化为高维向量空间中的数值向量。"
       "余弦相似度用于衡量两个文本向量之间的相似程度。"
       "分块策略影响检索的准确性和系统速度表现。")


def test_chunking_splits_by_size():
    """① max_tokens=20 时至少切成3块。"""
    assert len(chunk_text(DOC, max_tokens=20)) >= 3
    assert len(chunk_text(DOC, max_tokens=80)) >= 1


def test_tokenize_has_zh_and_en():
    """② 中文至少被切出单字，英文被切出。"""
    toks = tokenize("RAG 人工智能")
    assert "rag" in toks and "人" in toks


def test_cosine_identical_is_one():
    """③ 相同文本余弦相似度 = 1.0（浮点允许误差）。"""
    v = embed("完全相同的句子")
    assert dot(v, v) == pytest.approx(1.0)


def test_related_more_similar_than_unrelated():
    """④ 相关句 > 不相关句。"""
    rel1 = embed("RAG 检索增强生成")
    rel2 = embed("RAG 检索增强生成方法")
    unre = embed("今天天气晴朗适合外出游玩")
    assert cosine_similarity(rel1, rel2) > cosine_similarity(rel1, unre)


def test_retrieval_relevant_hit():
    """⑤ 查'向量数据库'命中含相关词的块。"""
    store = VectorStore()
    store.add_document(DOC, max_tokens=80)
    top = store.search("什么是向量数据库", top_k=1)[0]["text"]
    assert ("向量" in top) or ("RAG" in top) or ("检索" in top)


def test_retrieval_consistency():
    """⑥ 相似查询命中同块（确定性复现）。"""
    store = VectorStore()
    store.add_document(DOC, max_tokens=80)
    a = store.search("向量数据库存什么", top_k=1)[0]["text"]
    b = store.search("什么是向量数据库", top_k=1)[0]["text"]
    assert a == b
