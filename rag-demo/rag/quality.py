"""quality.py — RAG 答案质量打分（端到端问答）。

D4 验证"检索找得准不准"和"答案有没有幻觉"；D5 在此基础上评估：
    1. 答案相关性 —— 答案有没有答到问题里？（覆盖问题关键词）
    2. 综合质量门 —— 相关 + 忠实 加权打分，低于阈值判不合格

认知边界：
- 真实答案质量靠 LLM-as-Judge 或 embedding 语义相似度打分。
- 这里用"答案覆盖问题关键词的比例"近似相关性，离线可复现。
  它能可靠检测"答非所问 / 漏答"，但无法识别同义改写的答案。
"""
import re
from grounding import ground_claims, grounding_score


def _keywords(text):
    """极简分词：去标点 + 字母小写，保留中英文字符。"""
    text = text.lower()
    text = re.sub(r'[。！？；，、,.!?\n\s]+', ' ', text)
    return set(ch for ch in text if ch.isalnum())


def answer_relevance(answer, question):
    """答案覆盖问题关键词的比例。分母 = 问题词数。

    分母用问题不是答案，原因：相关性关注"有没有答到问题"，
    答得越多越可能覆盖问题。答案写得长不等于答到点上。
    """
    q = _keywords(question)
    a = _keywords(answer)
    if not q:
        return 0.0
    return len(a & q) / len(q)


def answer_relevance_breakdown(answer, question):
    """返回相关性 + 答案命中的问题词集合，便于调试。"""
    q = _keywords(question)
    a = _keywords(answer)
    if not q:
        return 0.0, set()
    hit = q & a
    return len(hit) / len(q), hit


def answer_completeness(answer, question):
    """答案是否覆盖了问题里的数字/实体（数字最容易被漏答）。

    纯数字场景：问题要"x 个并发"，答案没说 → 漏答。
    """
    q = _keywords(question)
    a = _keywords(answer)
    if not q:
        return 0.0
    return len(q & a) / len(q)


def composite_score(answer, question, context, weight_rel=0.5, weight_faith=0.5,
                    threshold=0.6):
    """综合质量分 = 相关 × w1 + 忠实 × w2。

    返回 (score, passed)：
      score = 0~1，passed = score >= threshold。
    """
    rel = answer_relevance(answer, question)
    faith = grounding_score(answer, context)
    score = weight_rel * rel + weight_faith * faith
    return round(score, 4), score >= threshold


class QualityGate:
    """质量门：给定阈值，判定答案合格不合格。

    用法：
        gate = QualityGate(threshold=0.6)
        gate.is_pass(answer, question, context)  # bool
        gate.score(answer, question, context)    # float
    """

    def __init__(self, threshold=0.6, weight_rel=0.5, weight_faith=0.5):
        self.threshold = threshold
        self.weight_rel = weight_rel
        self.weight_faith = weight_faith

    def score(self, answer, question, context):
        _, s = composite_score(answer, question, context,
                               self.weight_rel, self.weight_faith,
                               self.threshold)
        return s

    def is_pass(self, answer, question, context):
        _, passed = composite_score(answer, question, context,
                                    self.weight_rel, self.weight_faith,
                                    self.threshold)
        return passed


class StaticAnswerer:
    """固定答案的答案器（测试用，绕开真实 LLM）。"""

    def answer(self, question, contexts):
        """默认：把检索到的上下文直接拼成答案（最朴素答案器）。"""
        return "".join(c for c in contexts)


class CompositeAnswerer(StaticAnswerer):
    """基于上下文的合成答案器：把检索到的上下文整理成一句回答。

    它不编造——答案内容全部来自 contexts，因此接地的答案通常较高，
    适合端到端评估报告里代表“理想答案器”。要制造低分答案，用
    FabricatingAnswerer（测试内定义）。
    """

    def answer(self, question, contexts):
        return "".join(c for c in contexts)
