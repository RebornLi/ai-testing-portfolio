"""embedders.py — 嵌入层：真实模型加载 + 离线 mock 兜底"""
import numpy as np


class MockEmbedder:
    """确定性 mock 嵌入器：固定维、可离线、可复现。

    用于单元测试 —— 让 store 逻辑不依赖真实模型/服务/网络。
    维度固定 32，便于人眼理解。
    """

    dim = 32

    def embed(self, text):
        vec = np.zeros(self.dim, dtype=np.float32)
        for i, ch in enumerate(str(text)):
            vec[i % self.dim] += abs(ord(ch)) % 7
        if np.linalg.norm(vec) == 0:
            return vec
        return vec / np.linalg.norm(vec)

    def embed_batch(self, texts):
        return np.vstack([self.embed(t) for t in texts])


class HuggingFaceEmbedder:
    """真实嵌入器：加载 /models/Qwen3-Embedding-8B（lazy 加载）。

    ⚠️ 认知边界：具体 config 请对照官方文档验证。
    这里按 Qwen 系 embedding 的通用结构编写：
    - encoder(model) 输出 hidden states
    - 按 pooler/pooling 取 [CLS] 或 mean pooling
    - 归一化到单位向量
    维度约 4096。

    首次实例化加载模型（慢），之后 embed/embed_batch 复用权重。
    """

    def __init__(self, model_path="/models/Qwen3-Embedding-8B", max_length=512):
        self.model_path = model_path
        self.max_length = max_length
        self.model = None
        self.tokenizer = None
        self.dim = None
        self._load()

    def _load(self):
        import torch
        from transformers import AutoModel, AutoTokenizer
        torch.set_grad_enabled(False)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.model = AutoModel.from_pretrained(self.model_path).cuda().eval()
        # Qwen3-Embedding-8B 的输出维度（以实际为准）
        self.dim = self.model.config.hidden_size

    def _encode(self, text):
        import torch
        inputs = self.tokenizer(text, return_tensors="pt",
                                truncation=True, max_length=self.max_length)
        inputs = {k: v.cuda() for k, v in inputs.items()}
        with torch.no_grad():
            out = self.model(**inputs).last_hidden_state
            # mean pooling
            mask = inputs["attention_mask"].unsqueeze(-1)
            emb = (out * mask).sum(1) / mask.sum(1)
        return emb.cpu().numpy()[0]

    def embed(self, text):
        vec = self._encode(text)
        norm = np.linalg.norm(vec)
        return vec / norm if norm else vec

    def embed_batch(self, texts):
        return np.vstack([self.embed(t) for t in texts])


def get_embedder(mode="mock", **kwargs):
    """工厂函数：mock=离线测试，real=真实模型。"""
    if mode == "mock":
        return MockEmbedder()
    if mode == "real":
        return HuggingFaceEmbedder(**kwargs)
    raise ValueError(f"未知 mode: {mode}")
