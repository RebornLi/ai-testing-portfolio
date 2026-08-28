"""grounding.py — 确定性幻觉/接地检测。

"幻觉"= 答案里出现了上下文中**没有**的信息。这里用一个确定性关键词重叠
打分器，把句子级答案拆成"接地了"和"幻觉"两类，并给一个 0~1 接地分。

认知边界（重要）：
- 真实的 faithfulness / 幻觉检测通常用 LLM-as-Judge 或 embedding 语义相似度。
- 这里用 keyword-overlap 做教学替身：离线、可复现，能检测"答案编造了上下文里
  完全不存在的词"这类明显幻觉，但无法识别"同义改写的事实性幻觉"。
- 阈值 0.5 是我试出来的经验值，换领域应重新校准。
"""
import re


def _keywords(text):
    """去标点 + 去空白 + 字母小写，保留中英文字符。教学用极简分词。"""
    text = text.lower()
    text = re.sub(r'[。！？；，、,.!?\n\s]+', ' ', text)
    return set(ch for ch in text if ch.isalnum())


def split_claims(answer):
    """把答案切成句子（ claims ）。"""
    return [s.strip() for s in re.split(r'[。！？\n]', answer) if s.strip()]


def ground_claims(answer, context, threshold=0.5):
    """把答案每个句子判定"接地 / 幻觉"。

    返回 (grounded, hallucinated)：两个句子列表。
    判定：句子与上下文的关键词重叠比例 >= threshold → 接地。
    若无上下文，默认所有句子都幻觉（安全失败：没依据就不能断言）。
    """
    ctx_kw = _keywords(context)
    claims = split_claims(answer)
    if not ctx_kw:
        return [], list(claims)
    grounded, hallucinated = [], []
    for claim in claims:
        c_kw = _keywords(claim)
        if not c_kw:
            grounded.append(claim)  # 空句子不算幻觉
            continue
        ratio = len(c_kw & ctx_kw) / len(c_kw)
        (grounded if ratio >= threshold else hallucinated).append(claim)
    return grounded, hallucinated


def grounding_score(answer, context, threshold=0.5):
    """0~1 接地分 = 被接地的句子 ÷ 总句子数。1 = 无幻觉。"""
    grounded, hallucinated = ground_claims(answer, context, threshold)
    total = len(grounded) + len(hallucinated)
    if total == 0:
        return 1.0
    return len(grounded) / total
