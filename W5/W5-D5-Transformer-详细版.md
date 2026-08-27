# W5-D5 详细学习内容 · Transformer：Self-Attention 为什么是灵魂（6-8 小时版）

> 日期：2026-09-02（周三）｜ 主题：ML/DL 基础扫盲 —— Transformer / Attention
> 目标：吃透 Self-Attention 原理（Q/K/V、注意力权重），为什么比 RNN 强
> 验收：手算小 attention 权重（Q·K 点积 softmax）+ Transformer 流程图 + commit

---

## ⏰ 今日时间块（6-8 小时）

| 时间段 | 时长 | 内容 |
|---|---|---|
| 09:00-10:30 | 1.5h | 为什么需要 Attention：RNN 的瓶颈（串行、远距离丢信息） |
| 10:30-12:00 | 1.5h | Q / K / V 三件套 + 注意力权重怎么算 |
| 14:00-16:00 | 2h | 实战：numpy 手写 3 个 token 的 self-attention（Q·K→scale→softmax→×V） |
| 16:00-17:30 | 1.5h | 实战：多注意力（multi-head）直觉 + Transformer 主链路图 |
| 19:00-20:30 | 1.5h | 概念笔记⑤ 落盘（attention 原理 + 流程图） |
| 20:30-21:00 | 0.5h | 一句话笔记 + 学习日志 + commit |

---

## 一、为什么需要 Attention（1.5h）★ 今日重点

> 一句话：**Attention = 让每个词在"看"自己之前，先"看"所有其他词，然后决定有多关心谁。**

### RNN 的三大毛病（Attention 就是来治这些的）

| RNN 的问题 | 说明 |
|---|---|
| **串行** | 一步步读，不能并行，慢 |
| **远距离丢信息** | 读到句子末尾，句首信息早忘了（梯度消失） |
| **一刀切** | 处理每个词时，前后所有信息"平均"进一个向量，重点被稀释 |

> Transformer 的核心就是 **Self-Attention（自注意力）**，一次性让每个位置看到全部其他位置，长距离依赖一步搞定。

---

## 二、Q / K / V 三件套（1.5h）★ 核心

> 三个字母，是 attention 的灵魂。用大白话记：

| 符号 | 全称 | 大白话 |
|---|---|---|
| **Q** | Query | 每个词的"查询请求"——"我想知道什么" |
| **K** | Key | 每个词的"答案标签"——"我提供什么信息" |
| **V** | Value | 每个词的"实际内容"——"真正要输出的" |

### 注意力权重 = 每个词去"查"其他词的匹配度
- 词 A 的 Query 和词 B 的 Key 做点积 → 得到"A 关心 B 多少"的分数。
- 所有词对 A 的分数，做 **softmax** → 变成和为 1 的权重（注意力分布）。
- 用这个权重把**所有词的 V** 加权平均 → 得到 A 的"看过所有上下文之后的新表示"。

> 一句话：**Query 找 Key，命中越多越关心；关心后用 Value 表达。**

---

## 三、注意力怎么算：4 步（★ 产出）

```
step1  Q · K 点积     → 得到每个词对的原始分数（scores）
step2  ÷ √d_scale     → 缩放，防止数值过大（scale）
step3  softmax        → 分数变权重，和为 1
step4  × V 加权平均   → 得到新表示（attention 输出）
```

---

## 四、实战：numpy 手写 3 个 token 的 attention（2h）★ 产出①

> 给 3 个词，每个一个 4 维向量。手算 A 对 B、C 的注意力，看 A 最终表示怎么变。

```python
"""D5-手算 self-attention（3 token）· ML/DL 扫盲"""
import numpy as np

# 3 个 token，每个一个 4 维向量
X = np.array([
    [0.5, 0.1, 0.8, 0.2],   # token A
    [0.3, 0.9, 0.2, 0.6],   # token B
    [0.7, 0.2, 0.5, 0.4],   # token C
], dtype=float)

# 简单起见：Q = K = V = X（教学示意，真实模型用不同权重矩阵投影）
Q, K, V = X, X, X
d = Q.shape[1]                      # 维度 = 4

# step1: Q·K^T → scores
scores = Q @ K.T
# step2: 缩放
scores = scores / np.sqrt(d)
# step3: softmax（沿行）
def softmax(z):
    e = np.exp(z - np.max(z, axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)
attn = softmax(scores)

# step4: × V
out = attn @ V
print("注意力权重矩阵 softmax 后（每行和=1）:\n", np.round(attn, 3))
print("\nA 的最终表示（attention 输出第一行）:\n", np.round(out[0], 3))
```

**期望现象**：
- 注意力权重矩阵每行和 = 1。
- 第一个 token A 会"关注"自己最重（因为和自己的 Query/Key 最像）。

---

## 五、为什么 scale 要 ÷ √d（1.5h）

> 如果不缩放，点积分数随维度 d 增大而增大 → softmax 进入饱和区（梯度趋近 0）→ 学不动。
> ÷ √d 把方差拉回到 ~1，让梯度流通。这是 Transformer 能训起来的关键细节。

---

## 六、Transformer 主链路图（★ 产出）

```
输入句（词向量 + 位置编码）
        │
        ▼
   ┌─────────────────────────────────┐
   │  Self-Attention 层               │
   │  ① Q·K 点积 ② ÷√d ③ softmax ④ ×V │
   │  ⑤ Residual + LayerNorm          │
   └───────────────┬─────────────────┘
                   ▼
   ┌─────────────────────────────────┐
   │  Feed Forward 层                 │
   │  两层线性 + ReLU                 │
   └───────────────┬─────────────────┘
                   ▼
              （重复 N 次，通常 6-12 层）
                   ▼
   输出：每个词一个增强后的向量
```

> 多头注意力（Multi-Head）：不是算一组 Q/K/V，而是并行算 H 组（常 8 组），每组关注不同侧面（语法、语义、指代…），再拼起来。

---

## 七、概念笔记⑤ 落盘（1.5h）★ 产出

> 一句话记忆点：

1. **Self-Attention**：每个位置"看"全部其他位置，长距离依赖一次性拿到。
2. **Q/K/V**：Q 查询、K 标签、V 内容。Q 找 K，命中越重越关心。
3. **注意力权重**：Q·K 点积 → ÷√d 缩放 → softmax → ×V 加权平均。
4. **为什么比 RNN 强**：可并行、不丢远距离信息、重点不被稀释。
5. **多头注意力**：并行多组 Q/K/V，各看不同角度，拼起来更强。
6. **结构**：输入编码 → [Self-Attention + Feed Forward]×N → 输出。

---

## 八、面试口述版（大白话，别背术语）

> RNN 像一个人从左读到右，读到结尾忘了开头，还只能一步步读。
> Transformer 的 Attention 就像读一句话时，看每个词都能同时"瞥一眼"句子里所有其他词，然后判断"这个词跟谁关系最密"。
> 怎么判断？每个词有 Q（我想找什么）和 K（我有什么），Q 和 K 越配就越关心，关心的词用 V（真正内容）加权拼起来。
> 这就是为什么 Transformer 读长文本又快又准。

---

## ⏰ 今日验收清单

- [ ] 能口述"Q/K/V 各自是什么"
- [ ] 手算 attention：Q·K → scale → softmax → ×V 四步能走通
- [ ] Transformer 流程图已画（输入编码 → attention 堆叠 → 输出）
- [ ] 概念笔记⑤ 落盘（记忆点 ≥6 条）
- [ ] 学习日志写了（含卡点）
- [ ] 已 commit

## ⏰ 卡点提示

- 为什么 softmax 前要 scale？分数太大进入饱和区，梯度趋 0，模型学不动。
- attention 权重每行和为什么是 1？softmax 把分数变成概率分布。

## 📝 学习日志

> 今天（09-02 周三）：
> 1. 学 Transformer：RNN 串行、丢信息，Attention 一次性看全部位置。
> 2. Q 查询、K 标签、V 内容。Q·K 点积 → scale → softmax → ×V。
> 3. 用 numpy 手算了 3 个 token 的 attention，注意力权重每行和=1。
> 4. 卡点：为什么要 ÷√d？防止点积分数太大、softmax 饱和、梯度趋 0。
> 5. 明天 D6 写本周里程碑 + 复盘。

---
*创建于 W5-D5 · 计划：study 阶段二 W5 第 5 周*
