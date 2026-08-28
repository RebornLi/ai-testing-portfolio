"""store.py — 向量存储层：FAISS 封装 + 离线 mock 兜底"""
import numpy as np


class MockVectorStore:
    """离线向量库：内存列表 + 余弦相似度检索。

    对应 roadmap 组件 ChromaDB/FAISS 的教学简化版。
    """

    def __init__(self, dim=32):
        self.dim = dim
        self.vectors = []
        self.docs = []
        self.metadatas = []

    def add(self, vector, document, metadata=None):
        self.vectors.append(vector)
        self.docs.append(document)
        self.metadatas.append(metadata if metadata else {"text": document})
        return len(self.vectors)

    def add_embeddings(self, embeddings, documents):
        """一次加一组：(向量列表, 文档列表) 并行对应。"""
        for vec, doc in zip(embeddings, documents):
            self.add(vec, doc)
        return len(self.vectors)

    def search(self, query_vector, top_k=3):
        if not self.vectors:
            return []
        arr = np.asarray(self.vectors)
        sims = arr @ query_vector
        k = min(top_k, len(sims))
        idxs = np.argsort(sims)[::-1][:k]
        return [
            {
                "document": self.docs[i],
                "metadata": self.metadatas[i],
                "score": float(sims[i]),
            }
            for i in idxs
        ]

    def __len__(self):
        return len(self.vectors)


class FAISSVectorStore:
    """FAISS 封装（lazy 加载）。

    ⚠️ 认知边界：具体 API 名（IndexFlatCosine 等）请对照 FAISS 官方文档
    验证 —— 不同版本命名略有差异。

    add: 先归一化再 add
    search: search 拿 score，search_by_id 拿 id
    """

    def __init__(self, dim=4096):
        self.dim = dim
        self._index = None
        self.docs = {}
        self._import_faiss()

    def _import_faiss(self):
        try:
            import faiss
            self.faiss = faiss
        except ImportError:
            raise ImportError(
                "需要 faiss: pip install faiss-cpu。"
                "单元测试请用 MockVectorStore。"
            )

    def create_index(self):
        return self.faiss.IndexFlatCosine(self.dim)

    def add(self, vectors, documents=None):
        vectors = np.ascontiguousarray(vectors, dtype=np.float32)
        self.faiss.normalize_L2(vectors)   # 余弦检索先归一化
        self._index.add(vectors)
        if documents:
            start = len(self.docs)
            for i, d in enumerate(documents):
                self.docs[start + i] = d
        return len(self.docs)

    def search(self, query, top_k=3):
        q = np.ascontiguousarray([query], dtype=np.float32)
        self.faiss.normalize_L2(q)
        k = min(top_k, self._index.ntotal)
        scores, ids = self._index.search(q, k)
        return [
            {"id": int(ids[0][j]), "score": float(scores[0][j])}
            for j in range(len(ids[0]))
        ]

    def __len__(self):
        return self._index.ntotal if self._index else 0


def get_store(mode="mock", dim=32):
    """工厂函数：mock=离线测试，faiss=真实 FAISS。"""
    if mode == "mock":
        return MockVectorStore(dim=dim)
    if mode == "faiss":
        return FAISSVectorStore(dim=dim)
    raise ValueError(f"未知 mode: {mode}")
