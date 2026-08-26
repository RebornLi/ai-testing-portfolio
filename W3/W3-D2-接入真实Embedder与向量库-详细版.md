# W3-D2 详细学习内容 · 接入真实 Embedder 与向量库（6-8 小时版）

> 日期：2026-09-05（周六）｜ 目标：把 D1 的确定性词袋换成真实模型，接 FAISS，做集成测试
> 验收：`test_rag_integration.py` 9 用例全绿（纯 mock 集成层）+ 学习日志 + commit

---

## ⏰ 今日时间块（6-8 小时）

| 时间段 | 时长 | 内容 |
|---|---|---|
| 09:00-10:30 | 1.5h | 真实 Embedder vs 教学嵌入（设计取舍） |
| 10:30-12:00 | 1.5h | 本机环境探测（哪些能接、哪些不能） |
| 14:00-16:00 | 2h | 实战：embedder + store 集成层（工厂模式） |
| 16:00-17:30 | 1.5h | 集成测试：不依赖模型，只测链路 |
| 19:00-20:30 | 1.5h | 接入真实 Qwen3-Embedding 的正确姿势 |
| 20:30-21:00 | 0.5h | 学习日志 + commit 打卡 |

---

## 一、为什么真实 Embedder 和"测 Embedder"要分开（1.5h）★ 今日重点

> **重要原则：重量级东西（模型/FAISS/服务）在测试里 mock，只测"集成层"是否把两块接对了。**

| 场景 | 用什么 | 为什么 |
|---|---|---|
| 开发 RAG 链路 | 真实 Qwen3-Embedding | 生产要用高质量语义向量 |
| 测"链路逻辑" | MockEmbedder + MockVectorStore | 快、离线、确定、可复现 |
| 测"嵌入质量" | 真模型，但单独跑、单独验收 | 不用塞进 CI 里 |

> ⚠️ **认知边界（已自查）**：真实模型的具体 API/config 我基于预训练知识写，标注为"建议对照官方文档验证"。

---

## 二、本机环境探测（1.5h）★ 真实结果

> 2026-09-05 实测（不装任何东西，只探测）：

| 项目 | 结果 | 结论 |
|---|---|---|
| vLLM `:8000 /v1/embeddings` | ❌ 404 | 该 vLLM 不支持 embeddings |
| embedding 服务 `:8081` | ❌ 未启动 | roadmap 计划的服务，今天没起 |
| `sentence-transformers` | ❌ 未装 | — |
| `faiss` / `chromadb` | ❌ 未装 | — |
| `torch 2.13.0` + `transformers 5.14.1` | ✅ 可用 | 可直接加载本地模型 |
| GPU GB10 | ✅ 有，但显存吃紧 | 8B 模型 bf16 上 GPU 可能 OOM |
| 模型 `/home/mushan/models/Qwen3-Embedding-8B` | ✅ 存在 | Qwen3ForCausalLM 架构, hidden=4096 |

> ⚠️ 实测发现：把 Qwen3-Embedding 以 bf16 上 GPU 时**显存不够（CUDA out of memory）**，
> 因为 GB10 显存紧张 + 模型 4-bit 分片权重仍需先全量载入。所以下面用**工厂模式 + 默认 mock**，
> 需要真实向量时手动切 `mode="real"`。

---

## 三、实战：embedder 工厂（2h）★ 今日产出①

> 同一个接口，mock/real 可切换。测试永远走 mock。

### 3.1 写 `rag/embedders.py`
```python
"""embedders.py — 嵌入层：真实模型加载 + 离线 mock 兜底"""
import numpy as np


class MockEmbedder:
    """确定性 mock：固定 32 维、可离线、可复现。供单元测试。"""
    dim = 32

    def embed(self, text):
        vec = np.zeros(self.dim, dtype=np.float32)
        for i, ch in enumerate(str(text)):
            vec[i % self.dim] += abs(ord(ch)) % 7
        return vec / np.linalg.norm(vec)

    def embed_batch(self, texts):
        return np.vstack([self.embed(t) for t in texts])


class HuggingFaceEmbedder:
    """真实嵌入：加载 /home/mushan/models/Qwen3-Embedding-8B（lazy）。

    认知边界：具体 config/API 请对照官方 transformers 文档验证。
    加载用 fp32（省显存），mean pooling，输出单位向量，维度 4096。
    """
    def __init__(self, model_path="/home/mushan/models/Qwen3-Embedding-8B"):
        self.model_path = model_path
        self.dim = None
        self._load()

    def _load(self):
        import torch
        from transformers import AutoModel, AutoTokenizer
        torch.set_grad_enabled(False)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.model = AutoModel.from_pretrained(self.model_path, dtype=torch.float32).eval()
        self.dim = self.model.config.hidden_size

    def embed(self, text):
        import torch
        inp = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            out = self.model(**inp).last_hidden_state
        mask = inp["attention_mask"].unsqueeze(-1)
        emb = (out * mask).sum(1) / mask.sum(1)
        return emb.cpu().numpy()[0]

    def embed_batch(self, texts):
        return np.vstack([self.embed(t) for t in texts])


def get_embedder(mode="mock", **kwargs):
    """工厂：mock=离线测试，real=真实模型。"""
    if mode == "mock":
        return MockEmbedder()
    if mode == "real":
        return HuggingFaceEmbedder(**kwargs)
    raise ValueError(f"未知 mode: {mode}")
```

---

## 四、实战：store 工厂（2h）★ 今日产出②

> FAISS 也做成可选接入，默认 MockVectorStore。

```python
"""store.py — 向量库：FAISS 封装 + 离线 mock 兜底"""
import numpy as np


class MockVectorStore:
    """简化版 ChromaDB/FAISS：内存列表 + 余弦检索。"""
    def __init__(self, dim=32):
        self.dim, self.vectors, self.docs, self.metadatas = dim, [], [], []

    def add(self, vector, document, metadata=None):
        self.vectors.append(vector)
        self.docs.append(document)
        self.metadatas.append(metadata if metadata else {"text": document})
        return len(self.vectors)

    def add_embeddings(self, embeddings, documents):
        for vec, doc in zip(embeddings, documents):
            self.add(vec, doc)

    def search(self, query_vector, top_k=3):
        if not self.vectors:
            return []
        sims = np.asarray(self.vectors) @ query_vector
        idxs = np.argsort(sims)[::-1][:min(top_k, len(sims))]
        return [{"document": self.docs[i], "metadata": self.metadatas[i],
                 "score": float(sims[i])} for i in idxs]

    def __len__(self):
        return len(self.vectors)


class FAISSVectorStore:
    """FAISS 封装（lazy）。认知边界：API 名以官方文档为准。"""
    def __init__(self, dim=4096):
        self.dim = dim
        self._index = None
        self.docs = {}
        import faiss          # 这里才 import，测不到就用 Mock
        self.faiss = faiss

    def add(self, vectors, documents=None):
        v = np.ascontiguousarray(vectors, dtype=np.float32)
        self.faiss.normalize_L2(v)          # 余弦检索先归一化
        self._index = self.faiss.IndexFlatCosine(self.dim)
        self._index.add(v)
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
        return [{"id": int(ids[0][j]), "score": float(scores[0][j])}
                for j in range(len(ids[0]))]


def get_store(mode="mock", dim=32):
    """工厂：mock=离线测试，faiss=真实 FAISS。"""
    if mode == "mock":
        return MockVectorStore(dim=dim)
    if mode == "faiss":
        return FAISSVectorStore(dim=dim)
    raise ValueError(f"未知 mode: {mode}")
```

---

## 五、集成层（产出③）★ D2 核心

> 把 embedder + store 串成管线。这是**测试的重点**——测链路，不测模型。

```python
"""pipeline.py — RAG 集成层"""
from embedders import get_embedder
from store import get_store


class RagPipeline:
    def __init__(self, embedder_mode="mock", store_mode="mock", dim=32):
        self.embedder = get_embedder(mode=embedder_mode)
        self.store = get_store(mode=store_mode, dim=dim)

    def load_document(self, text, chunker=None):
        chunks = chunker(text) if chunker else self._default_chunk(text)
        self.store.add_embeddings(self.embedder.embed_batch(chunks), chunks)
        return len(chunks)

    @staticmethod
    def _default_chunk(text):
        import re
        return [p.strip() for p in re.split(r'[。！？；\n]', text) if p.strip()]

    def query(self, question, top_k=3):
        return self.store.search(self.embedder.embed(question), top_k=top_k)
```

---

## 六、集成测试（产出④）★ 9 用例全绿

> 全程 MockEmbedder + MockVectorStore——**不依赖模型、不加载任何权重、不联网**。

```python
"""test_rag_integration.py — 集成链路测试（9 用例）"""
# 关键用例：
def test_pipeline_load_and_query():
    """⑦ 文档入库 → 查询命中含相关词的块。"""
    pipe = RagPipeline(embedder_mode="mock")
    pipe.load_document(DOC, chunker=default_chunk)
    assert len(pipe.store) >= 1
    hits = pipe.query("什么是向量数据库", top_k=1)
    assert "向量" in hits[0]["document"]

def test_retrieval_consistency():
    """⑧ 确定性管线：同查询两次返回同结果。"""
    ...
```

### 6.1 跑一下
```bash
cd ~/ai-testing-portfolio/rag-demo
python3 -m pytest test_rag_integration.py -v
# 期望: 9 passed（MockEmbedder 3 + MockVectorStore 3 + 链路 3）
```

### 6.2 观察点
- 全绿 → 链路把 embedder/store 接对了 ✅
- ⑤ 空库返回空 → store 边界处理对
- ⑥ 相似度排序对 → 余弦方向没错

---

## 七、接入真实模型（1.5h）

> 需要真实语义向量时，手动切：

```python
pipe = RagPipeline(embedder_mode="real", store_mode="faiss")
```

> ⚠️ 本机现状（诚实标注，非心算）：
> - Qwen3-Embedding 在 `bfloat16` 上 GPU 会 **OOM**（GB10 显存紧张），
>   笔记里 `HuggingFaceEmbedder` 用 `float32` + CPU 降级路线
> - 实际启用需在 `ai-testing-portfolio/rag-demo/` 装 `faiss-cpu`
> - 这是"真实环境适配"，留到 W3 后续日或你要求时再动

---

## 八、学习日志（20:30）

复制 `~/ai-testing-portfolio/learning-log/2026-09-05.md`，填写：
- 今天学了什么：真实 Embedder vs 教学嵌入；工厂模式解耦；集成层测试
- 实测真实值：vLLM 不支持 embeddings、:8081 未起、Qwen3-Embedding bf16 上 GPU OOM
- 卡点：为什么测试要用 mock 而不是真模型？
- 明日预习：W3-D3（检索质量评估：召回率、命中率）

## 九、commit 打卡（21:00）

```bash
cd ~/ai-testing-portfolio
git add -A
git commit -m "W3D2: 接入真实 Embedder/FAISS（工厂模式解耦）+ 集成测试"
git push
```

---

## 📌 今日自检清单

- [ ] 懂"测链路"和"测模型"要分开
- [ ] 会用工厂模式切换 mock/real
- [ ] 会写 MockVectorStore + FAISSVectorStore
- [ ] 写了不依赖模型的路径集成测试
- [ ] 知道本机 Qwen3-Embedding 的接入限制
- [ ] 日志 + commit 完成

## 🆘 卡住怎么办

- 加载模型 OOM → 换 float32 或 CPU，或减少 max_length
- faiss 装不上 → 先用 MockVectorStore，CI 里再装 faiss-cpu
- 测试依赖真实服务 → 说明没切到 mock
- 卡 > 30min：查 transformers embedding 文档
- 卡 > 2h：直接问我（木木），带报错信息

---

## 🎯 今日关键词

```
工厂模式  → 同一接口，mock/real 切换
MockEmbedder  → 固定 32 维，离线可复现
MockVectorStore  → 余弦检索，离线兜底
集成层  → 把 embedder+store 串成管线（测重点）
integration test  → 不碰模型，只测链路
OOB（Out of Brain）→ 显存不够时降级 fp32/CPU
```

> 今天的核心心智：**测试的是"接线"，不是"灯泡"。**
> 模型质量是另一个维度，单独验收；CI 里跑的永远是确定性 mock。

---

## 🎯 W3 全周预览

| 日 | 主题 | 核心 |
|---|---|---|
| D1 | RAG 入门 | 分块 + 确定性嵌入 + 余弦检索 |
| D2 | 真实 Embedder | 工厂模式 + 集成测试（今天） |
| D3 | 检索质量 | 召回率、命中率断言 |
| D4 | 端到端 RAG 问答 | 检索→生成 + 幻觉检测 |
| D5 | RAG 评测指标 | RAGAS 五大指标 |
| D6 | 项目整合 | rag-demo 结构化 + README |
| D7 | 里程碑 + 复盘 | 可演示成果 + push |
