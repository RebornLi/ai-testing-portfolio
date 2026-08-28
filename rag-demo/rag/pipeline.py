"""pipeline.py — RAG 集成层：embedder + store 串起来。

这是 D2 的核心 —— 把"嵌入"和"存储/检索"接成一个可复用组件。
测试重点就是这个集成层是否把两块正确接上了。
"""
from embedders import get_embedder
from store import MockVectorStore, get_store


class RagPipeline:
    """最小 RAG 管线：文档入库 → 问题检索。

    设计：embedder 与 store 都支持 mock，测试不依赖任何模型/服务。
    """

    def __init__(self, embedder_mode="mock", store_mode="mock", dim=32):
        self.embedder = get_embedder(mode=embedder_mode)
        self.store = get_store(mode=store_mode, dim=dim)
        self.dim = dim

    def load_document(self, text, chunker=None):
        """把一个文档入库。返回存入的块数。"""
        chunks = chunker(text) if chunker else self._default_chunk(text)
        vectors = self.embedder.embed_batch(chunks)
        self.store.add_embeddings(vectors, chunks)
        return len(chunks)

    @staticmethod
    def _default_chunk(text):
        import re
        parts = re.split(r'[。！？；\n]', text)
        return [p.strip() for p in parts if p.strip()]

    def query(self, question, top_k=3):
        """查一个问题，返回最相似的检索结果。"""
        qv = self.embedder.embed(question)
        return self.store.search(qv, top_k=top_k)


def default_chunk(text):
    import re
    parts = re.split(r'[。！？；\n]', text)
    return [p.strip() for p in parts if p.strip()]
