# W6-D5 详细学习内容 · DeepEval 框架 & 自动化评测（6-8 小时版）

> 日期：2026-09-08（周二）｜ 主题：Agent 评测 —— DeepEval 实战
> 目标：理解 DeepEval、接 pytest、写确定性评测用例并跑出分数
> 验收：`eval-lab/` 自动化 DeepEval 脚本（确定性 metric）+ 跑绿 + 概念笔记 + commit

---

## ⏰ 今日时间块（6-8 小时）

| 时间段 | 时长 | 内容 |
|---|---|---|
| 09:00-10:30 | 1.5h | DeepEval 是什么、评测链路 TestCase → Metric → evaluate |
| 10:30-12:00 | 1.5h | TestCase 三个核心字段 + LLMTestCase vs ConversationalTestCase |
| 14:00-16:00 | 2h | 实战：写确定性 metric，跑通一次 evaluate 出分数 |
| 16:00-17:30 | 1.5h | 实战：接 pytest，写一组 DeepEval 用例 |
| 19:00-20:30 | 1.5h | 概念笔记⑤ 落盘（DeepEval 速记） |
| 20:30-21:00 | 0.5h | 学习日志 + commit |

---

## 一、DeepEval 是什么（1.5h）★ 今日重点

> 一句话：**DeepEval 是"给 LLM 写测试"的 pytest 式框架**——把评测用例封装成对象，用 assert 风格的 metric 打分。

### 评测链路的三个核心概念

```
TestCase（用例）→ Metric（打分规则）→ evaluate（跑一轮）
```

- **TestCase**：一组输入/输出，和一个"该对"的预期。
- **Metric**：判断这个答案对不对的规则（确定性规则，或调 LLM）。
- **evaluate**：把一组 TestCase 跑一遍，输出通过率、平均分。

### 三种 metric 写法（重要，直接决定能不能跑通）

| 类型 | 依赖 | 要不要 key | 适合 |
|---|---|---|---|
| 确定性 metric（自写） | 规则代码 | ❌ 不要 | 离线、确定性评测 |
| 现成 metric（LLM 类） | 调 OpenAI/LLM | ✅ 要 | 幻觉/相关性 |
| 现成 metric（规则类） | 字符串比较 | ❌ 不要 | 精确匹配 |

> **关键**：没有 key 也能做完整评测——写一个确定性 metric 即可。这正是 W6 的风格：确定性、可复现。

---

## 二、TestCase 怎么构造（1.5h）★ 核心

> LLM 单轮用例要有三个字段：输入、实际输出、预期输出。

```python
from deepeval.test_case import LLMTestCase

tc = LLMTestCase(
    input="我喜欢哪个城市",           # input：用户问什么
    actual_output="我喜欢北京",         # actual_output：模型实际答什么
    expected_output="我喜欢北京",       # expected_output：应该答什么
)
```

> - `input`：用户的输入。
> - `actual_output`：模型实际给出的答案。
> - `expected_output`：预期/标准答案（确定性 metric 用它算对不对）。
> - 多轮对话用 `ConversationalTestCase`（一轮一轮攒输入输出）。

---

## 三、为什么必须写 `async def a_measure`（2h）★ 今日踩坑★

> ⚠️ **deepeval 4.2.0 的坑**：你只写 `def measure()` 还不够！框架默认走异步，会报
> `object float can't be used in await` 或 `Async execution ... not supported`。
>
> **根因**：框架调的是 `a_measure`（异步方法），自定义 metric 必须**同时实现**
> `async def a_measure`，并在里面**同步委托** `self.measure(tc)`。

### 错误的写法（会报错）

```python
class MyMetric(BaseMetric):
    def measure(self, tc):            # 只写 measure ❌
        return 1.0
    # 缺 a_measure → 报 "Async execution ... not supported"
```

### 正确的写法（实测通过）

```python
"""自定义确定性 metric：不依赖 key，不依赖 LLM"""
from deepeval.metrics import BaseMetric


class KeywordMetric(BaseMetric):
    """规则：答案是否包含指定关键词。score=1 通过 / 0 失败。"""
    def __init__(self, keyword, name="keyword"):
        self.name = name
        self.threshold = 1.0
        self.score, self.success, self.reason = 0.0, False, ""
        self.keyword = keyword.lower()

    def measure(self, tc):
        # 确定性规则：答案包含关键词 → 1.0
        self.score = 1.0 if self.keyword in tc.actual_output.lower() else 0.0
        self.success = self.score >= self.threshold
        self.reason = f"命中关键词 '{self.keyword}'" if self.score == 1.0 \
            else f"未命中关键词 '{self.keyword}'"
        return self.score

    async def a_measure(self, tc):      # 关键：必须是 async def，内部委托 measure
        return self.measure(tc)

    def successful(self):               # 框架据此判断 pass/fail
        return self.success
```

> 记住三件套：**`measure` 写规则 + `async def a_measure` 委托 + `successful` 返回成功**。

---

## 四、跑通一次 evaluate（2h）★ 产出①

```python
"""用自定义 metric 跑一次 evaluate，不用 key。

★ 踩坑：evaluate() 返回 EvaluationResult（pydantic 模型），**没有 .success** 属性。
  单条结果在 res.test_results 列表里，每条有 .success / .score。
  整体通过率要自己算：通过条数 / 总条数。
"""
from deepeval import evaluate
from deepeval.test_case import LLMTestCase

tc_ok = LLMTestCase(input="我喜欢哪个城市", actual_output="我喜欢北京", expected_output="我喜欢北京")
tc_bad = LLMTestCase(input="我喜欢哪个城市", actual_output="我不确定", expected_output="我喜欢北京")

# 一组用例（可以多个）
test_cases = [tc_ok, tc_bad]

for tc in test_cases:
    res = evaluate([tc], metrics=[KeywordMetric(keyword="北京")])  # 跑一轮
    passed = res.test_results[0].success     # 单条的通过状态（不是 res.success！）
    print(f"答案={tc.actual_output!r}  通过={passed}")

# 整体通过率 = 通过条数 / 总条数
res = evaluate(test_cases, metrics=[KeywordMetric(keyword="北京")])
pass_count = sum(1 for tr in res.test_results if tr.success)
overall = pass_count / len(res.test_results)
print(f"\n整体通过率: {overall:.0%}")
print("期望: 北京→True, 我不确定→False, 整体 50%")
assert overall == 0.5, "通过率应是 50%"
print("DeepEval evaluate 跑通 ✅")
```

**期望**：`我喜欢北京`→True，`我不确定`→False，整体 50%。

---

## 五、接 pytest：一组自动评测（1.5h）★ 产出

> DeepEval 用例本质是对象，可以塞进 pytest 参数化。下面写一个"答案质量门"：

```python
"""pytest 式答案质量门：每个用例答案必须命中关键词"""
import pytest


def make_tc(actual, keyword="北京"):
    return LLMTestCase(
        input="我喜欢哪个城市",
        actual_output=actual,
        expected_output="我喜欢北京",
    )


@pytest.mark.parametrize("actual, expected_ok", [
    ("我喜欢北京", True),
    ("北京是我的家乡", True),
    ("我不确定", False),
])
def test_answer_gate(actual, expected_ok):
    tc = make_tc(actual)
    m = KeywordMetric(keyword="北京")
    res = evaluate([tc], metrics=[m])
    # 注意：evaluate() 返回 EvaluationResult，单条结果在 .test_results 里
    passed = res.test_results[0].success
    assert passed == expected_ok, f"{actual!r} 的预期与实测不符"


if __name__ == "__main__":
    # 不装 pytest 也能直接跑
    test_answer_gate("我喜欢北京", True)
    test_answer_gate("我不确定", False)
    print("pytest 式答案质量门 ✅（可直接 python 运行或 pytest 跑）")
```

> 有 `pytest` 时用 `pytest test_eval.py`；没环境时 `python test_eval.py` 也能验证断言。

---

## 六、多轮上下文用例（1.5h）★ 产出

> Agent 是多轮对话。用 `ConversationalTestCase` 攒一轮轮输入输出。

```python
"""多轮用例：ConversationalTestCase 用 turns 记录每一轮。

★ 踩坑：
  - 不传 input / actual_output，要传 `turns`（一个 Turn 列表）。
  - 每个 Turn 用 role（user/assistant）+ content，不是 input/actual_output。
"""
from deepeval.test_case import ConversationalTestCase, Turn

tc_multi = ConversationalTestCase(
    scenario="认识一下",
    turns=[
        Turn(role="user", content="我叫小明"),
        Turn(role="assistant", content="你好小明"),
        Turn(role="user", content="我喜欢哪个城市？"),
        Turn(role="assistant", content="你之前说喜欢北京"),
    ],
)

# 给这个多轮用例做"上下文连贯"确定性检查：
# 第2轮（assistant）是否呼应前面 -> 提到"北京"= 记得住上下文
m = KeywordMetric(keyword="北京", name="context")
m.reason = "检查第2轮是否呼应上下文"
print(f"多轮用例轮数: {len(tc_multi.turns)}")
print(f"第2轮答案: {tc_multi.turns[3].content}")

# 验证：第2轮（assistant）提到"北京"= 记得住上下文
assert "北京" in tc_multi.turns[3].content
print("多轮上下文用例构建 ✅")
```

> 多轮上下文评测的关键：`input` 和 `actual_output` 都是**列表**，一轮一轮对齐。

---

## 七、概念笔记⑤ 落盘（1.5h）★ 产出

> 一句话记忆点：

1. **DeepEval = 给 LLM 写测试的 pytest 框架**：TestCase（用例）+ Metric（打分）+ evaluate（跑一轮）。
2. **三个字段**：input（问什么）/ actual_output（答什么）/ expected_output（该答什么）。
3. **evaluate() 返回 EvaluationResult（pydantic），没有 .success 属性**：单条结果在 .test_results 列表里，每条 .success / .score；整体通过率 = 通过条数 / 总条数。
3. **踩坑**：自定义 metric 必须写 `async def a_measure` 委托 `measure`，否则报 await 错误。
4. **不带 key**也能做评测——写确定性 metric（规则代码），不依赖真实 LLM。
5. **三种 metric**：确定性自写（不需要 key）、现成规则类（不需要 key）、现成 LLM 类（需要 key）。
6. **多轮用 `ConversationalTestCase`**：input/actual_output 都是列表，一轮一轮对齐。

---

## 八、面试口述版（大白话）

> DeepEval 就像给大模型装的"pytest"。你把"给模型一个问题、一个标准答案"做成一个测试用例，
> 再写一条规则判断它答得对不对。evaluate 一次就跑完一堆用例，得出通过率。
> 关键技巧是，没模型 key 也能测——写死一条规则（比如答案里有没有这个词）当评分器，
> 照样能跑出分数、做质量门。这就是离线可复现的评测。

---

## ⏰ 今日验收清单

- [ ] 能讲清 DeepEval 的 TestCase/Metric/evaluate 链路
- [ ] 写了一个确定性 metric（measure + async a_measure + successful 三件套）
- [ ] 没配 key 也跑通了一次 evaluate，分数对
- [ ] 接 pytest 写了质量门
- [ ] 用了 ConversationalTestCase 做多轮用例
- [ ] 概念笔记⑤ 落盘
- [ ] 学习日志写了（含卡点）
- [ ] 已 commit

## ⏰ 卡点提示

- **async 报错**：`object float can't be used in await` → 你的 `a_measure` 要 `async def`（不是普通 `def`）。
- **不支持异步**：`Async execution ... not supported` → 缺 `a_measure`，要补 async 版委托 measure。

## 📝 学习日志

> 今天（09-08 周二）：
> 1. 学 DeepEval——给 LLM 写测试的 pytest 框架：TestCase + Metric + evaluate。
> 2. 写了确定性 metric（不依赖 key），关键是 `async def a_measure` 委托 `measure`。
> 3. 跑通 evaluate，"我喜欢北京"→True，"我不确定"→False，整体 50%。
> 4. 接 pytest 写答案质量门。
> 5. 用 ConversationalTestCase 做多轮用例（input/actual_output 是列表）。
> 6. 卡点：自定义 metric 必须 async 写 a_measure，否则 await 报错。
> 7. 明天 D6 本周里程碑 + 开源贡献（提 issue）。

---
*创建于 W6-D5 · 计划：AI 求职阶段二 W6 第 6 周*
