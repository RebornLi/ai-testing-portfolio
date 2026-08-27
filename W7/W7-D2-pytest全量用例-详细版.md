# W7-D2 详细学习内容 · pytest 全量用例 + CI 门禁（6-8 小时版）

> 日期：2026-08-28（周五）｜ 主题：用 pytest 写全量用例 + 接入 CI 门禁
> 目标：11 个用例覆盖四维度，`pytest tests/ -q` 全绿才能作为门禁
> 验收：`pytest tests/ -q` → 11 passed；`.github/workflows/` CI 文件就绪

---

## ⏰ 今日时间块（6-8 小时）

| 时间段 | 时长 | 内容 |
|---|---|---|
| 09:00-10:30 | 1.5h | pytest 是什么：参数化、conftest、CI 门禁 |
| 10:30-12:00 | 1.5h | 为什么"全绿才能合并"——门禁的价值 |
| 14:00-16:00 | 2h | 实战：写工具调用维度用例（3 个） |
| 16:00-17:30 | 1.5h | 实战：写记忆 + 成本延迟维度用例 |
| 19:00-20:30 | 1.5h | 实战：写 DeepEval 离线兜底用例 |
| 20:30-21:00 | 0.5h | 学习日志 + commit |

---

## 一、pytest 与 CI 门禁（1.5h）★ 今日重点

> 一句话：**pytest 全绿 = 门禁放行。CI 就是那个"不绿不放行"的机器人。**

### 门禁模型

```
push / PR → GitHub Actions 触发
         → 装依赖（pip install -r requirements.txt）
         → pytest tests/ -q
         → exit 0（全绿）→ 允许合并
         → exit 非0（有失败）→ 阻止合并
```

> 好处：**代码再改坏评测，也进不了主分支。** 人眼会漏，CI 不会。

---

## 二、工具调用维度用例（2h）★ 产出①

```python
"""tests/test_tool_calling.py — 维度1"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "system"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent import ReActAgent, DeterministicPlanner
from metrics import ToolCallingMetric


def build(steps, max_iter=10):
    return ReActAgent(DeterministicPlanner(steps), max_iterations=max_iter)


def test_tool_calling_good_passes():
    """好 agent：加乘链正确（name/args/result/顺序 全对）"""
    agent = build([
        ("tool", "add", {"a": 3, "b": 4}),
        ("tool", "multiply", {"a": 7, "b": 2}),
        ("answer", "结果是14"),
    ])
    traj = agent.run("算")["trajectory"]
    expected = [
        {"name": "add", "args": {"a": 3, "b": 4}, "result": 7},
        {"name": "multiply", "args": {"a": 7, "b": 2}, "result": 14},
    ]
    score, passed, errors = ToolCallingMetric(expected).score(traj)
    assert passed and score == 1.0, (score, passed)
    assert errors == []


def test_tool_calling_wrong_args_fails():
    """坏 agent：参数错误 → 抓出来。"""
    agent = build([
        ("tool", "add", {"a": 1, "b": 2}),   # 错：期望 3,4
        ("answer", "错"),
    ])
    traj = agent.run("算")["trajectory"]
    expected = [{"name": "add", "args": {"a": 3, "b": 4}, "result": 7}]
    score, passed, errors = ToolCallingMetric(expected).score(traj)
    assert not passed and score == 0.0
    assert any("参数" in e for e in errors)


def test_tool_calling_missing_call_fails():
    """坏 agent：漏掉 multiply → 次数不匹配被抓住。"""
    agent = build([
        ("tool", "add", {"a": 3, "b": 4}),
        ("answer", "只加"),
    ])
    traj = agent.run("算")["trajectory"]
    expected = [
        {"name": "add", "args": {"a": 3, "b": 4}, "result": 7},
        {"name": "multiply", "args": {"a": 7, "b": 2}, "result": 14},
    ]
    score, passed, errors = ToolCallingMetric(expected).score(traj)
    assert not passed
    assert any("次数" in e for e in errors)
```

---

## 三、记忆 + 成本延迟维度用例（1.5h）★ 产出②

```python
"""tests/test_memory_and_cost.py — 维度2 + 维度3"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "system"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent import Memory, MemoryAgent
from metrics import MemoryMetric, CostLatencyMetric


class RememberingPlanner:
    """记住关键信息供后续轮读取。"""
    turn = 1
    def __call__(self, prompt, memory, maxit):
        if self.turn == 1:
            memory.write("name", "小明")
            memory.write("city", "北京")
            self.turn += 1
            return {"answer": "记下"}
        city = memory.read("city")
        self.turn += 1
        return {"answer": f"你喜欢{city}" if city else "忘了"}


class ForgettingPlanner:
    """不写记忆，必然失忆。"""
    turn = 1
    def __call__(self, prompt, memory, maxit):
        self.turn += 1
        return {"answer": "我不知道"}


def test_memory_good():
    """好 agent 记住城市，同一个 agent 跨轮能读到。"""
    mem = Memory()
    planner = RememberingPlanner()
    MemoryAgent(mem, planner).run("第1轮")
    MemoryAgent(mem, planner).run("第2轮")
    assert MemoryAgent(mem, planner).run("第3轮")["answer"] == "你喜欢北京"
    score, passed, errors = MemoryMetric(mem, {"name": "小明", "city": "北京"}).score()
    assert passed and score == 1.0, (score, passed)


def test_memory_bad_fails():
    """坏 agent 不写记忆 → 失忆。"""
    mem = Memory()
    MemoryAgent(mem, ForgettingPlanner()).run("第1轮")
    score, passed, errors = MemoryMetric(mem, {"name": "小明"}).score()
    assert not passed and score == 0.0
    assert any("忘记" in e for e in errors)


def test_cost_latency_good():
    """成本延迟都在预算内。"""
    m = CostLatencyMetric(cost=0.5, latency=1.0)
    score, passed, _ = m.score()
    assert passed and score == 1.0


def test_cost_latency_bad():
    """成本超预算 → 不达标。"""
    m = CostLatencyMetric(cost=2.0, latency=1.0, cost_budget=1.0)
    score, passed, errors = m.score()
    assert not passed
    assert any("成本" in e for e in errors)
```

---

## 四、DeepEval 离线兜底用例（1.5h）★ 产出③

```python
"""tests/test_deepeval.py — 维度4（离线确定性兜底，无需 key）"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from metrics import DeepEvalMetric


def test_deepeval_keyword_hit():
    """命中关键词 → 通过。"""
    m = DeepEvalMetric(actual="我喜欢北京", expected="北京", keyword="北京")
    score, passed, errors = m.score()
    assert passed and score == 1.0
    assert errors == []


def test_deepeval_keyword_miss():
    """未命中关键词 → 不通过。"""
    m = DeepEvalMetric(actual="我不确定", expected="北京", keyword="北京")
    score, passed, errors = m.score()
    assert not passed and score == 0.0
    assert any("命中" in e for e in errors)


def test_deepeval_exact_match():
    """无关键词兜底：精确匹配。"""
    m = DeepEvalMetric(actual="北京", expected="北京")
    score, passed, _ = m.score()
    assert passed
    m2 = DeepEvalMetric(actual="上海", expected="北京")
    score2, passed2, _ = m2.score()
    assert not passed2
```

---

## 五、概念笔记② 落盘（1.5h）★ 产出

> 一句话记忆点：
> 1. **pytest 全绿 = 门禁放行**，CI 是不长眼力的机器人。
> 2. 用例覆盖四维度 = 工具调用 / 记忆 / 成本 / DeepEval，坏 agent 必须被判失败。
> 3. 有状态 `DeterministicPlanner` 每 `run()` 必须新实例（D1 的坑延续到测试里）。
> 4. 指标统一 `(score, passed, errors)`，测试直接 `assert passed`。

---

## 六、验收清单

- [x] 11 用例覆盖四维度（3 + 4 + 3 分布）
- [x] 坏 agent 用例确实被判失败（断言抓住）
- [ ] 本地 `pytest tests/ -q` → 11 passed
- [ ] 概念笔记② 落盘
- [ ] 学习日志写了（含卡点）
- [ ] 已 commit

## ⏰ 卡点提示

- 测记忆时**同一个 agent 跨轮**才共享 `memory`，新建 agent 就断。
- 测工具调用时**别复用同一个 agent run 两次**，第二次空答案。

## 📝 学习日志

> 今天（08-28 周五）：
> 1. 学 pytest + CI 门禁：全绿才能合并，CI 是机器人守门。
> 2. 写 11 用例：工具调用 3 个、记忆+成本 4 个、DeepEval 3 个。
> 3. 坏 agent 用例都正确被判失败（参数错 / 漏调用 / 失忆 / 未命中）。
> 4. 延续 D1 坑：有状态规划器每次 run 新实例。
> 5. 明天 D3 上 Docker，让评测离线可复现。

---
*创建于 W7-D2 · 计划：AI 求职阶段二 W7 第 7 周*
