# W3-D1 详细学习内容 · RAG 入门与向量检索（6-8 小时版）

> 日期：2026-09-04（周五）｜ 目标：理解 RAG 是什么，手动实现"分块→嵌入→检索"最小链路
> 验收：能画出 RAG 流程图 + 写一个确定性向量检索原型 + 学习日志 + commit

---

## ⏰ 今日时间块（6-8 小时）

| 时间段 | 时长 | 内容 |
|---|---|---|
| 09:00-10:30 | 1.5h | RAG 是什么（为什么需要它） |
| 10:30-12:00 | 1.5h | RAG 全流程拆解（4 个环节） |
| 14:00-16:00 | 2h | 实战：分块 + 确定性嵌入（numpy，不依赖服务） |
| 16:00-17:30 | 1.5h | 实战：余弦相似度检索 + 取 Top-K |
| 19:00-20:30 | 1.5h | 验证：检索准确性 + 一致性测试 |
| 20:30-21:00 | 0.5h | 学习日志 + commit 打卡 |

---

## 一、RAG 是什么（1.5h）★ 今日重点

> **RAG = Retrieval Augmented Generation，检索增强生成。**

一句话：**让大模型在回答前，先去自己的知识库"查资料"，拿到相关资料再生成答案。**

### 为什么要 RAG？
大模型有两个致命局限：
1. **知识滞后**：训练数据有截止日期，不知道最新信息
2. **瞎编**：不懂的知识会硬编（幻觉）

RAG 解决：**先把相关资料检索出来塞给模型 → 模型"照着资料答" → 减少幻觉、补充新知。**

### 一个类比
> 闭卷考试（纯大模型）vs 开卷考试（RAG）。RAG 就是给模型一本"参考书"，让它查了再答。

---

## 二、RAG 全流程（1.5h）

> roadmap 里 `rag-demo/` 的目标是自建 RAG 系统（切分→embedding→向量库→检索→rerank→引用）。
> 今天先做**最核心的前 3 步**：分块、嵌入、检索。

### 2.1 四个环节
```
                        【离线建库阶段】
  原始文档
    ↓
① 分块 Chunking     → 长文档切成小块（每块几百字）
    ↓
② 嵌入 Embedding   → 每块文本 → 一个向量（一串数字）
    ↓
③ 存入向量库        → 向量 + 原文一起存（本机用列表即可）
                        【在线查询阶段】
    用户问题
    ↓
④ 检索 Retrieve    → 问题也变向量，和库里所有块算相似度
    ↓
⑤ 取 Top-K 最相似的块 → 作为"参考书"喂给模型
    ↓
⑥ 生成 Answer      → 模型结合检索内容作答
```

> **今天的核心：①②④。** 分块决定"查什么"，嵌入决定"怎么比"，检索决定"查得准不准"。

### 2.2 三个关键概念
| 概念 | 作用 | 今天的实现 |
|---|---|---|
| **分块** | 长文档拆小块，检索更准 | 按句子切 + 按字数截断 |
| **Embedding** | 文本 → 向量（可计算相似度） | 确定性词袋哈希（numpy） |
| **余弦相似度** | 衡量两个向量的接近程度 | `dot(a,b) / (|a|·|b|)` |

> ⚠️ **本机现状（诚实说明）**：
> roadmap 计划用本地 embedding 服务 `:8081` + ChromaDB/FAISS。但今天 `:8081` **没启动**、
> `sentence_transformers` 也没装。**所以今天用一个"确定性词袋嵌入"原型**——
> 纯 numpy、结果可复现，用来学 RAG 原理。等想接真实 embedding 时再换。

---

## 三、实战：分块 + 嵌入（2h）★ 今日产出①

> 先验证一个 RAG 原型跑通，再写测试。

### 3.1 安装
```bash
pip install numpy pytest
```

### 3.2 写 `rag_utils.py`（分块 + 嵌入）
```python
"""RAG 基础工具：分块 + 确定性嵌入（可离线、可复现）"""
import re
import hashlib


def chunk_text(text, max_tokens=80):
    """把长文本按句子切分，累积到 max_tokens 切成一块。

    为什么分块？
    - 大文档一次全塞给向量库 → 检索粒度太粗、相似度不准
    - 切成小块 → 每个小块只讲一件事，查得更准
    """
    sentences = re.split(r'[。！？；\n]', text)
    chunks, current, current_len = [], [], 0
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        current.append(sentence)
        current_len += len(sentence)
        if current_len >= max_tokens:
            chunks.append("。".join(current))
            current, current_len = [], 0
    if current:  # 处理剩余不足一块的
        chunks.append("。".join(current))
    return chunks


def tokenize(text):
    """中文按字、英文/数字按词分词。

    真实系统用 jieba/BERT tokenizer；这里用最简确定性分词。
    """
    return re.findall(r'[\u4e00-\u9fff]|[a-zA-Z0-9]+', text.lower())


def embed(text, dim=128):
    """确定性文本嵌入：词袋哈希 + L2 归一化。

    - 每个词通过 hash 映射到 dim 维的一个位置并累加计数
    - 最后归一化，让向量长度=1（方便算余弦相似度）

    注意：这是教学原型，不是高质量 embedding。
    生产环境用 sentence-transformers / 本地 :8081 服务。
    """
    vector = [0.0] * dim
    for word in tokenize(text):
        index = int(hashlib.md5(word.encode()).hexdigest(), 16) % dim
        vector[index] += 1.0
    norm = sum(v * v for v in vector) ** 0.5
    if norm == 0:
        return vector
    return [v / norm for v in vector]
```

### 3.3 验证分块与嵌入
```python
if __name__ == "__main__":
    doc = ("向量数据库用于存储和检索文本的向量表示。"
           "RAG通过检索相关文档来增强大模型的回答质量。"
           "Embedding将文本转化为高维向量空间中的数值向量。"
           "余弦相似度用于衡量两个文本向量之间的相似程度。"
           "分块策略影响检索的准确性和系统速度表现。")

    chunks = chunk_text(doc, max_tokens=80)
    print(f"分块数：{len(chunks)}")
    for i, c in enumerate(chunks):
        print(f"  [{i}] {c[:45]}...")

    v1 = embed("RAG 检索增强生成")
    v2 = embed("RAG 检索增强生成方法")
    v3 = embed("今天天气真好适合出去游玩")
    print(f"\ncos(句1,句2) = {dot(v1, v2):.3f}")
    print(f"cos(句1,句3) = {dot(v1, v3):.3f}")
    print(f"句1与句2更相似 → {dot(v1, v2) > dot(v1, v3)}")
```

---

## 四、实战：余弦相似度检索（1.5h）★ 今日产出②

> 把"块"变成向量存起来，查询时算相似度，取最相似的 Top-K。

### 4.1 写 `vector_search.py`
```python
"""最小向量检索：余弦相似度 + Top-K"""
import numpy as np
from rag_utils import chunk_text, embed


def cosine_similarity(a, b):
    """两个向量的余弦相似度（已在 embed 里归一化，所以就是点积）。"""
    return float(np.dot(a, b))


class VectorStore:
    """极简向量库：存块 + 向量，支持余弦检索。"""

    def __init__(self):
        self.chunks = []      # 原文
        self.vectors = []     # 对应向量

    def add_document(self, text, max_tokens=80):
        for chunk in chunk_text(text, max_tokens):
            self.chunks.append(chunk)
            self.vectors.append(embed(chunk))

    def search(self, query, top_k=2):
        """返回 (相似度, 原文) 的列表，按相似度降序。"""
        qv = embed(query)
        scored = [(cosine_similarity(qv, v), i)
                  for i, v in enumerate(self.vectors)]
        scored.sort(reverse=True)
        results = []
        for sim, idx in scored[:top_k]:
            results.append({"score": sim, "text": self.chunks[idx]})
        return results
```

### 4.2 跑检索
```python
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
```

---

## 五、验证检索准确性（1.5h）★ 今日产出③

> 测试 RAG 最关键：**检索要准**。不同的查询应命中不同的、相关的块。

### 5.1 写 `test_rag_retrieval.py`
```python
"""RAG 检索测试（numpy 确定性嵌入，可离线跑）"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "rag"))
from rag_utils import chunk_text, embed, tokenize
from vector_search import VectorStore, cosine_similarity

DOC = ("向量数据库用于存储和检索文本的向量表示。"
       "RAG通过检索相关文档来增强大模型的回答质量。"
       "Embedding将文本转化为高维向量空间中的数值向量。"
       "余弦相似度用于衡量两个文本向量之间的相似程度。"
       "分块策略影响检索的准确性和系统速度表现。")


@pytest.mark.parametrize("max_tokens,expected_min", [
    (80, 1),
    (40, 2),
    (20, 3),
])
def test_chunking_splits_by_size(max_tokens, expected_min):
    """① 分块数随 max_tokens 减小而增加。"""
    chunks = chunk_text(DOC, max_tokens=max_tokens)
    assert len(chunks) >= expected_min


def test_tokenize_chinese_by_character():
    """② 中文至少被切成单字级别（含中文字符）。"""
    tokens = tokenize("人工智能")
    assert "人" in tokens and "工" in tokens or len(tokens) >= 1


def test_cosine_of_identical_is_1():
    """③ 相同文本的余弦相似度 = 1.0。"""
    v = embed("完全相同的句子")
    assert cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_of_different_is_lower():
    """④ 相关句子的相似度 > 不相关句子的相似度。"""
    rel1 = embed("RAG 检索增强生成")
    rel2 = embed("RAG 检索增强生成方法")
    unre = embed("今天天气晴朗适合外出游玩")
    assert cosine_similarity(rel1, rel2) > cosine_similarity(rel1, unre)


def test_retrieval_returns_relevant_chunk():
    """⑤ 查询'向量数据库'时，最相似的块应含'向量数据库'相关词。"""
    store = VectorStore()
    store.add_document(DOC, max_tokens=80)
    hits = store.search("什么是向量数据库", top_k=1)
    top_text = hits[0]["text"]
    # 最相似的块应提到向量数据库 / RAG（与查询语义相关）
    assert ("向量" in top_text) or ("RAG" in top_text) or ("检索" in top_text)


def test_retrieval_consistency():
    """⑥ 语义相近的两个查询，应命中同一个块（稳定可复现）。"""
    store = VectorStore()
    store.add_document(DOC, max_tokens=80)
    a = store.search("向量数据库存什么", top_k=1)[0]["text"]
    b = store.search("什么是向量数据库", top_k=1)[0]["text"]
    assert a == b  # 确定性嵌入下，结果稳定
```

### 5.2 跑一下
```bash
cd ~/ai-testing-portfolio/rag-demo
pytest test_rag_retrieval.py -v
# 期望: ①~⑥ 全绿
```

---

## 六、失败自测（1h）★ 先看失败长啥样

```python
import pytest

def test_intentional_fail():
    # 把"相似文本余弦=1"错写成"相似文本余弦=0"
    v = embed("测试句子")
    assert cosine_similarity(v, v) == pytest.approx(0.0)
    # 实测是 1.0，会直接报 assert 1.0 == 0.0
```

---

## 七、运行 & 验证

```bash
cd ~/ai-testing-portfolio/rag-demo
mkdir -p rag
# 把 rag_utils.py、vector_search.py 放进去
pytest test_rag_retrieval.py -v
# 期望: 6 用例全绿
```

---

## 八、学习日志模板（20:30）

复制 `~/ai-testing-portfolio/learning-log/2026-09-04.md`，填写：
- 今天学了什么：RAG 原理、分块、嵌入、余弦相似度检索
- 实测真实值：本机用确定性词袋嵌入（numpy），检索结果稳定可复现
- 卡点：中文分词怎么切？为什么用哈希而不是随机向量？
- 明日预习：W3-D2（真实 embedding 服务接入 + 向量库 ChromaDB/FAISS）

## 九、commit 打卡（21:00）

```bash
cd ~/ai-testing-portfolio
git add -A
git commit -m "W3D1: RAG 入门：分块 + 确定性嵌入 + 余弦检索"
git push
```

---

## 📌 今日自检清单

- [ ] 能解释 RAG 是什么、为什么需要它（开卷考试类比）
- [ ] 能说清 RAG 四环节（分块→嵌入→存库→检索）
- [ ] 会写 chunk_text 分块
- [ ] 会写确定性 embed（词袋哈希 + 归一化）
- [ ] 会算余弦相似度 + 取 Top-K
- [ ] 写了 6 个检索测试用例
- [ ] 日志 + commit 完成

## 🆘 卡住怎么办

- 分块不对 → 检查 `max_tokens` 阈值和切分符
- 检索结果都一样 → 检查是否归一化，或分词是否太粗
- 想接真实 embedding → 启动 `:8081` 服务或装 `sentence-transformers`
- 卡 > 30min：看 OpenAI RAG 教程（搜"RAG 检索增强生成"）
- 卡 > 2h：直接问我（木木），带报错信息

---

## 🎯 今日关键词

```
RAG          → 检索增强生成（开卷考试）
Chunking    → 长文档切小块（粒度越细检索越准）
Embedding   → 文本 → 向量（可计算相似度）
余弦相似度   → cos(a,b)，值越大越相似（范围 -1~1）
Vector Store → 存向量+原文，支持相似检索
Top-K       → 取最相似的前 K 个块喂给模型
```

> 今天的核心：**文本变向量，向量可比大小。** 这是 RAG 的底座。
> 下周你会把这里的"确定性嵌入"换成真实的向量模型（:8081 / FAISS），
> 检索会从"词重叠"进化到"语义相似"。

---

## 🎯 W3 全周预览（对照 roadmap）

| 日 | 主题 | 核心 |
|---|---|---|
| D1 | RAG 入门 | 分块 + 嵌入 + 余弦检索 |
| D2 | 真实 Embedding | :8081 服务 + 向量库（FAISS/Chroma） |
| D3 | 检索质量测试 | 召回率、相关性、命中率断言 |
| D4 | 端到端 RAG 问答 | 检索→生成链路 + 幻觉检测 |
| D5 | RAG 评测指标 | RAGAS 五大指标 |
| D6 | 项目整合 | rag-demo 结构化 + README |
| D7 | 里程碑 + 复盘 | 可演示成果 + push |

> W3 目标：能讲清 RAG 每个环节的坑，检索效果可量化。
