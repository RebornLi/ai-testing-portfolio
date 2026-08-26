# W3-D4 详细学习内容 · 端到端 RAG 问答 + 幻觉检测（6-8 小时版）

> 日期：2026-09-07（周一）｜ 目标：把“检索 + 答案 + 接地检测”串成端到端流水线，检测答案幻觉
> 验收：`test_rag_d4.py` 9 用例全绿 + 学习日志 + commit

---

## ⏰ 今日时间块（6-8 小时）

| 时间段 | 时长 | 内容 |
|---|---|---|
| 09:00-10:30 | 1.5h | 幻觉是什么（检索 vs 生成两个错误源） |
| 10:30-12:00 | 1.5h | 接地（grounding）概念 + 为什么要有幻觉检测 |
| 14:00-16:00 | 2h | 实战：确定性接地检测（句子级重叠打分） |
| 16:00-17:30 | 1.5h | 端到端流水线：检索→答案→接地评分 |
| 19:00-20:30 | 1.5h | 失败自测 + 边界（无上下文、同义改写） |
| 20:30-21:00 | 0.5h | 学习日志 + commit 打卡 |

---

## 一、幻觉是什么（1.5h）★ 今日重点

> **幻觉（hallucination）**：模型说出了听起来对、但上下文里**没有依据**的话。
> RAG 有两个错误源，今天集中攻第二个：
> 1. **检索错误**：找错了资料 → D3 已测（召回/命中率）
> 2. **生成幻觉**：找对了资料，却答了资料外的东西 → **今天测这个**

> 幻觉是 RAG 的头号杀手。没有幻觉检测 = 盲开。

### 1.1 两类幻觉
- **编造（fabrication）**：答案包含上下文完全没有的信息
- **矛盾（contradiction）**：答案跟上下文说法打架

> 今天用确定性方法做**第一类**——上下文里没有的词 = 可疑幻觉。

---

## 二、接地（grounding）+ 检测原理（1.5h）

> **接地** = 让答案的每个论断都“踩”在证据上。断言越靠近上下文，越可信。

```
答案句子 → 与上下文做关键词重叠打分 → 打分 >= 阈值 = 接地，否则 = 幻觉
接地分 = 被接地的句子 ÷ 总句子数   （1 = 零幻觉）
```

### 2.1 为什么用关键词重叠？
> 真实系统用 **LLM-as-Judge** 或 **embedding 语义相似度** 做幻觉检测。
> 今天我们用**关键词重叠**做教学替身：离线、可复现、能检测"编造了上下文完全不存在的词"。

> ⚠️ **认知边界（重要）**：
> - 关键词重叠**认不出同义改写**的幻觉（如"哈希表"↔"键值对"），这是它的天花板。
> - 阈值 0.5 是我试出来的经验值，换领域要重新校准。
> - 没有上下文时，安全失败：**默认全部判幻觉**（没依据就不能断言）。

---

## 三、实战：确定性接地检测（2h）★ 今日产出①

> 核心就是一个模块：`rag/grounding.py`。

### 3.1 写 `rag/grounding.py`
```python
"""grounding.py — 确定性幻觉/接地检测"""
import re


def _keywords(text):
    """去标点 + 去空白，保留中英文字符。教学用极简分词。"""
    text = text.lower()
    text = re.sub(r'[。！？；，、,.!?\n\s]+', ' ', text)
    return set(ch for ch in text if ch.isalnum())


def split_claims(answer):
    """把答案切成句子（claims）。"""
    return [s.strip() for s in re.split(r'[。！？\n]', answer) if s.strip()]


def ground_claims(answer, context, threshold=0.5):
    """把答案每个句子判定“接地 / 幻觉”。

    返回 (grounded, hallucinated) 两个句子列表。
    判定：句子与上下文关键词重叠比例 >= threshold → 接地。
    无上下文 → 全部判幻觉（安全失败）。
    """
    ctx_kw = _keywords(context)
    claims = split_claims(answer)
    if not ctx_kw:
        return [], list(claims)
    grounded, hallucinated = [], []
    for claim in claims:
        c_kw = _keywords(claim)
        if not c_kw:
            grounded.append(claim)
            continue
        ratio = len(c_kw & ctx_kw) / len(c_kw)
        (grounded if ratio >= threshold else hallucinated).append(claim)
    return grounded, hallucinated


def grounding_score(answer, context, threshold=0.5):
    """0~1 接地分 = 被接地的句子 ÷ 总句子数。1 = 零幻觉。"""
    grounded, hallucinated = ground_claims(answer, context, threshold)
    total = len(grounded) + len(hallucinated)
    if total == 0:
        return 1.0
    return len(grounded) / total
```

### 3.2 跑一下看效果
```python
from grounding import ground_claims, grounding_score
ctx = "向量数据库用于存储检索文本向量。RAG检索相关文档增强回答。"
ans = "向量数据库用于存储检索文本向量。圆周率约等于3.14159。"
g, h = ground_claims(ans, ctx)
print("接地:", g)      # ['向量数据库用于存储检索文本向量']
print("幻觉:", h)      # ['圆周率约等于3.14159']
print("接地分:", grounding_score(ans, ctx))  # 0.5
```

> 观察：编造的"圆周率"与上下文零重叠 → 被判幻觉。这是确定性可复现的。

---

## 四、端到端流水线（1.5h）★ 产出②

> 串起来：问题 → 检索 → 答案 → 接地评分。

```python
"""pipeline.py 增加 answerer + 接地检测（D4 产出②）"""
# pipeline.py 已含 RagPipeline / default_chunk（来自 D1-D3）
# D4 新增：给流水线加"答案层"，并在查完后做接地评分


class RagPipeline:
    def __init__(self, embedder_mode="mock", store_mode="mock", dim=32):
        self.embedder = get_embedder(mode=embedder_mode)
        self.store = get_store(mode=store_mode, dim=dim)

    def load_document(self, text, chunker=None):
        chunks = chunker(text) if chunker else self._default_chunk(text)
        self.store.add_embeddings(self.embedder.embed_batch(chunks), chunks)

    def query(self, question, top_k=3):
        return self.store.search(self.embedder.embed(question), top_k=top_k)

    def answer(self, question, answerer, top_k=3):
        """检索到的上下文喂给 answerer，返回答案。"""
        hits = self.query(question, top_k=top_k)
        contexts = [h["document"] for h in hits]
        return answerer.answer(question, contexts)
```

> 关键：答案器是**可插拔**的——单元测试用假答案器，真实用 LLM。

---

## 五、集成测试（产出③）★ 9 用例全绿

> 全程 mock + 确定性 grounding，不依赖真实模型。

```python
"""test_rag_d4.py — 端到端 + 幻觉检测，9 用例"""
from grounding import ground_claims, grounding_score, split_claims
from pipeline import RagPipeline, default_chunk

CONTEXT = ("向量数据库用于存储和检索文本的向量表示。"
           "RAG 通过检索相关文档来增强大模型的回答质量。"
           "Embedding 将文本转化为高维向量空间中的数值向量。")

def test_split_claims():
    """① 答案按句子拆分。"""
    assert split_claims("第一句。第二句。") == ["第一句", "第二句"]

def test_no_context_all_hallucination():
    """② 无上下文 → 安全失败，全部判幻觉。"""
    g, h = ground_claims("向量数据库是啥。", "")
    assert g == [] and len(h) == 1

def test_grounding_full():
    """③ 答案全部来自上下文 → 全接地，得分 1.0。"""
    ans = "向量数据库用于存储检索文本向量。RAG 检索相关文档增强回答。"
    g, h = ground_claims(ans, CONTEXT)
    assert h == []
    assert grounding_score(ans, CONTEXT) == pytest.approx(1.0)

def test_grounding_partial():
    """④ 混入编造 → 至少一句幻觉，分 < 1。"""
    ans = "向量数据库用于存储检索文本向量。圆周率约等于3.14159。"
    g, h = ground_claims(ans, CONTEXT)
    assert len(h) >= 1
    assert grounding_score(ans, CONTEXT) < 1.0

def test_grounding_score_range():
    """⑤ 接地分永远落在 [0, 1]。"""
    assert 0.0 <= grounding_score("哈希表 缓存 无关", CONTEXT) <= 1.0
    assert 0.0 <= grounding_score("向量数据库 检索 无关", CONTEXT) <= 1.0

def test_more_fabrication_lower_score():
    """⑥ 编造越多，接地分越低。"""
    clean = "向量数据库用于检索文本向量。RAG 检索文档。"
    dirty = "向量数据库检索文本向量。圆周率约等于3.14159。太阳系有八大行星。"
    assert grounding_score(dirty, CONTEXT) < grounding_score(clean, CONTEXT)

def test_end_to_end_pipeline_grounds_context():
    """⑦ 走完整流水线，接地答案分高。"""
    pipe = RagPipeline(embedder_mode="mock")
    pipe.load_document(CONTEXT, chunker=default_chunk)
    hits = pipe.query("什么是向量数据库", top_k=1)
    ans = "".join(h["document"] for h in hits)
    assert grounding_score(ans, CONTEXT) >= 0.9

def test_end_to_end_detects_fabrication():
    """⑧ 答案混入上下文没有的内容（圆周率）→ 接地分低。"""
    fabricated = "向量数据库用于检索文本向量。圆周率约等于3.14159。"
    assert grounding_score(fabricated, CONTEXT) < 1.0

def test_pipeline_answerer_interface():
    """⑨ 答案器有统一接口 answer(question, contexts)。"""
    class StaticAnswerer:
        def answer(self, question, contexts):
            return "占位答案无关内容"
    StaticAnswerer().answer("q", ["c"])  # 不报错
```

### 5.1 跑一下
```bash
cd ~/ai-testing-portfolio/rag-demo
pytest test_rag_d4.py -v
# 期望: 9 passed
```

---

## 六、失败自测（1h）

```python
def test_intentional_fail():
    # 把"无上下文全幻觉"错写成"全接地"
    g, h = ground_claims("向量数据库是啥。", "")
    assert g == ["向量数据库是啥。"]  # 应为 []
```

---

## 七、运行 & 验证

```bash
cd ~/ai-testing-portfolio/rag-demo
pytest test_rag_d4.py -v
# 期望: 9 passed
```

### 关键观察点
- 全绿 → 句子拆分 + 接地判定 + 端到端流水线都对了 ✅
- 无上下文时**默认幻觉**：这是安全设计，不是 bug
- 想升级检测精度 → 把 `_keywords` 换成真实 embedding 语义相似度

---

## 八、学习日志模板（20:30）

复制 `~/ai-testing-portfolio/learning-log/2026-09-07.md`，填写：
- 今日学了什么：幻觉两个来源、接地打分、确定性幻觉检测
- 实测真实值：编造"圆周率约等于3.14159"与上下文零重叠 → 被判幻觉
- 卡点：关键词重叠认不出同义改写怎么办？
- 明日预习：W3-D5（端到端问答 + 答案质量：相关性/忠实度打分）

## 九、commit 打卡（21:00）

```bash
cd ~/ai-testing-portfolio
git add -A
git commit -m "W3D4: 端到端 RAG 流水线 + 确定性幻觉/接地检测"
git push
```

---

## 📌 今日自检清单

- [ ] 能讲清幻觉两个来源（检索错 / 生成幻觉）
- [ ] 会写句子级接地打分
- [ ] 知道"无上下文=安全失败"
- [ ] 写了确定性幻觉检测（不依赖模型）
- [ ] 串了端到端流水线
- [ ] 日志 + commit 完成

## 🆘 卡住怎么办

- 分词太粗 → 换 jieba 或真实 tokenizer
- 幻觉漏报（同义改写）→ 换 embedding 语义相似度
- 阈值难定 → 先跑一批 golden 答案，观察分数分布再定
- 卡 > 30min → 想清楚"幻觉 = 上下文里没有依据"
- 卡 > 2h → 问木木，带报错信息

---

## 🎯 今日关键词

```
幻觉 hallucination → 答案超出上下文依据
接地 grounding     → 让答案踩在证据上
grounding_score    → 接地句子 ÷ 总句子（1=零幻觉）
split_claims       → 按句子拆分答案
安全失败           → 没上下文就先默认幻觉
LLM-as-Judge       → 真实幻觉检测的升级方案
```

> 今天给 RAG 装上了"照妖镜"：答案再漂亮，过不了接地检测就是不合格。
> 没有幻觉检测的 RAG，等于无证驾驶。

---

## 🎯 W3 全周预览

| 日 | 主题 | 核心 |
|---|---|---|
| D1 | RAG 入门 | 分块 + 确定性嵌入 + 余弦检索 |
| D2 | 真实 Embedder | 工厂模式 + 集成测试 |
| D3 | 检索质量 | Recall/Precision/MRR/HitRate |
| D4 | 幻觉检测 | 确定性接地打分（今天） |
| D5 | 端到端问答 | 答案质量 + 忠实度 |
| D6 | RAG 评测 | 端到端质量分 + 报告 |
| D7 | 里程碑 + 复盘 | 可演示成果 + push |
