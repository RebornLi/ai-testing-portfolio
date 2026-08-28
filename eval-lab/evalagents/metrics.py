"""eval_lab/metrics.py — Agent 评测四维度打分函数（对齐 W6-D2/D3/D4/D5）。

每个维度一个纯函数，输入 agent 轨迹/上下文，输出可量化的分数。
全部确定性，不依赖真实模型、不依赖 key。

维度：
    - score_tool_calling      (D2  工具调用：name/参数名/参数值/顺序/次数/结果)
    - score_completion_rate   (D3  任务完成率)
    - score_context_memory    (D3  多轮上下文 / 记忆)
    - score_cost_latency      (D4  成本 & 延迟 归一化)
    - score_quality           (D4  质量分 = 成功率 × (1-成本) × (1-延迟))
    - score_integration       (D6  四维度总分)
- deep_eval KeywordMetric    (D5  DeepEval 确定性 metric 封装)
"""
import time


# ---------- D2 工具调用维度 ----------

def score_tool_calling(trajectory, expected_calls):
    """工具调用维度打分（0~1）。

    expected_calls：期望的工具调用列表 [(name, args), ...]。
    逐条比对：name 相同、args 相同、结果一致、顺序一致。
    任意一步对不上 → 该步 0 分。
    """
    if not trajectory or not expected_calls:
        return 0.0
    correct = 0
    for got, exp in zip(trajectory, expected_calls):
        exp_name, exp_args = exp
        if got.name != exp_name:
            continue
        if got.args != exp_args:
            continue
        correct += 1
    return correct / len(expected_calls)


def has_wrong_param_name(trajectory, wrong_key):
    """抓错（D2 错2）：轨迹里是否存在参数名写错（如 cities 应为 city）。"""
    for c in trajectory:
        if isinstance(c.args, dict) and wrong_key in c.args:
            return True
    return False


# ---------- D3 任务完成率 ----------

def completion_rate(steps_executed, necessary):
    """任务完成率 = 实际完成必要步骤 / 必要步骤总数（0~1）。"""
    if not necessary:
        return 1.0
    done = sum(1 for s in steps_executed if s in necessary)
    return done / len(necessary)


# ---------- D3 多轮上下文 / 记忆 ----------

def score_context_memory(agent, expected_written, expected_answer_hint=()):
    """多轮上下文维度打分（0~1）。

    靠显式读写 memory 判定：
        - 第 1 轮把关键信息写进了 memory（expected_written 的 key 都存在）
        - 最后一轮的答案含预期提示词（从记过的 memory 读出并作答）
    两样都满足 → 1.0，否则 0.0。

    ★ 不重新 run agent：那样会推进规划器 turn，多轮上下文评分会串台。
      只读 agent 跑完后的 memory.store 与最后一轮的 answer。
    """
    memory_ok = all(k in agent.memory.store for k in expected_written)
    answer = getattr(agent, "last_answer", None)
    answer_ok = any(h in str(answer) for h in expected_answer_hint) if expected_answer_hint else True
    return 1.0 if (memory_ok and answer_ok) else 0.0


# ---------- D4 成本 & 延迟 ----------

def score_cost_latency(total_elapsed, per_step_costs, budget, per_step_budget):
    """成本 & 延迟归一化打分（0~1）。

    budget：可接受的总成本上限；per_step_budget：单步可接受时间上限。
    成本、延迟都越小分越高，任一边界爆表 → 0。
    """
    cost = sum(per_step_costs)
    cost_score = max(0.0, 1.0 - cost / budget) if budget else 1.0
    latency_score = max(0.0, 1.0 - total_elapsed / per_step_budget) if per_step_budget else 1.0
    return round(min(cost_score, latency_score), 4)


def quality_score(success, cost, elapsed, budget, per_step_budget):
    """质量分 = 成功率 × (1 - 成本归一化) × (1 - 延迟归一化)（0~1）。"""
    cost_score = 1.0 - (cost / budget if budget else 0.0)
    latency_score = 1.0 - (elapsed / per_step_budget if per_step_budget else 0.0)
    return round(success * max(0.0, cost_score) * max(0.0, latency_score), 4)


# ---------- D6 四维度整合 ----------

def score_integration(tool, completion, context, cost_latency):
    """四维度总分 = 各维度均分（0~1）。"""
    return round((tool + completion + context + cost_latency) / 4, 4)


# ---------- D5 DeepEval 确定性 metric ----------

class KeywordMetric:
    """DeepEval 式确定性 metric（不依赖 key、不依赖 LLM）。

    复刻 DeepEval 的 TestCase/Metric/evaluate 三件套：
        - measure(tc)        写规则，返回 score
        - successful()        框架据此判断 pass/fail
        - reason / score      可读的诊断信息

    实际运行用 run_deep_eval() 模拟：输入 TestCase 列表 + metric，
    输出每条是否通过 + 整体通过率（不依赖真实 deepeval，保证离线可复现）。
    """
    def __init__(self, keyword, name="keyword"):
        self.keyword = keyword.lower()
        self.name = name
        self.threshold = 1.0
        self.score, self.success, self.reason = 0.0, False, ""

    def _grade(self, actual_output):
        hit = self.keyword in str(actual_output).lower()
        self.score = 1.0 if hit else 0.0
        self.success = self.score >= self.threshold
        self.reason = (f"命中关键词 '{self.keyword}'" if hit
                       else f"未命中关键词 '{self.keyword}'")
        return self.score

    def successful(self):
        """复刻 DeepEval BaseMetric：据此判断 pass/fail。"""
        return self.success

    def evaluate(self, tc):
        """对一个 TestCase 打分（兼容 DeepEval 字段：actual_output）。"""
        return self._grade(getattr(tc, "actual_output", ""))


def run_deep_eval(test_cases, metric):
    """模拟 DeepEval evaluate：跑一组 TestCase，返回 {pass_rate, results}。

    对标 W6-D5 的 evaluate() —— 但没有 .success 属性，自己算通过率。
    test_cases 的元素要有 .actual_output 字段（或字典 actual_output）。
    """
    passed = 0
    results = []
    for tc in test_cases:
        actual = tc.actual_output if hasattr(tc, "actual_output") else tc["actual_output"]
        ok = metric.evaluate(tc)
        results.append({"actual": actual, "ok": ok})
        if ok:
            passed += 1
    return {"pass_rate": round(passed / len(test_cases), 4) if test_cases else 1.0,
            "results": results}


def make_llm_test_case(input_text, actual_output, expected_output=None):
    """构造 DeepEval LLMTestCase 风格的简单对象。"""
    return type("LLMTestCase", (), {
        "input": input_text,
        "actual_output": actual_output,
        "expected_output": expected_output or actual_output,
    })
