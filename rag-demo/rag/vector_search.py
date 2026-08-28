"""最小向量检索：余弦相似度 + Top-K"""
import numpy as np
from rag_utils import chunk_text, embed


def cosine_similarity(a, b):
    return float(np.dot(a, b))


class VectorStore:
    def __init__(self):
        self.chunks = []
        self.vectors = []

    def add_document(self, text, max_tokens=80):
        for chunk in chunk_text(text, max_tokens):
            self.chunks.append(chunk)
            self.vectors.append(embed(chunk))

    def search(self, query, top_k=2):
        qv = embed(query)
        scored = [(cosine_similarity(qv, v), i)
                  for i, v in enumerate(self.vectors)]
        scored.sort(reverse=True)
        results = []
        for sim, idx in scored[:top_k]:
            results.append({"score": sim, "text": self.chunks[idx]})
        return results


if __name__ == "__main__":
    store = VectorStore()
    doc = ("向量数据库用于存储和检索文本的向量表示。"
           "RAG通过检索相关文档来增强大模型的回答质量。"
           "Embedding将文本转化为高维向量空间中的数值向量。"
           "余弦相似度用于衡量两个文本向量之间的相似程度。"
           "分块策略影响检索的准确性和系统速度表现。")
    store.add_document(doc)
    print(f"共存入 {len(store.chunks)} 个块\n")
    for q in ["什么是向量数据库?", "如何度量文本相似性?", "RAG 的核心优势是?"]:
        hits = store.search(q, top_k=1)
        top = hits[0]
        print(f"'{q}' → 命中相似度={top['score']:.3f}")
        print(f"    回答: {top['text'][:45]}...\n")
