"""RAG 基础工具：分块 + 确定性嵌入（可离线、可复现）"""
import re
import hashlib


def chunk_text(text, max_tokens=80):
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
    if current:
        chunks.append("。".join(current))
    return chunks


def tokenize(text):
    return re.findall(r'[\u4e00-\u9fff]|[a-zA-Z0-9]+', text.lower())


def embed(text, dim=128):
    vector = [0.0] * dim
    for word in tokenize(text):
        index = int(hashlib.md5(word.encode()).hexdigest(), 16) % dim
        vector[index] += 1.0
    norm = sum(v * v for v in vector) ** 0.5
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def dot(a, b):
    import numpy as np
    return float(np.dot(a, b))


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
    print(f"cos(句1,句2) = {dot(v1, v2):.3f}")
    print(f"cos(句1,句3) = {dot(v1, v3):.3f}")
    print(f"句1与句2更相似 → {dot(v1, v2) > dot(v1, v3)}")
