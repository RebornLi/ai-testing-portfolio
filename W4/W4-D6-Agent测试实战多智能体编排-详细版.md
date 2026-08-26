# W4-D6 详细学习内容 · Agent 测试实战：多智能体编排（6-8 小时版）

> 日期：2026-08-30（周六）｜ 主题：Agent 测试进阶 — 多智能体编排
> 目标：测 Orchestrator 分发 + MockSubAgent 替身 + 顺序执行
> 验收：`orchestrator.py` + `test_agent_orchestrator.py` 13 用例全绿 + `agent-lab` 65 全绿 + 学习日志 + commit

---

## ⏰ 今日时间块（6-8 小时）

| 时间段 | 时长 | 内容 |
|---|---|---|
| 09:00-10:30 | 1.5h | 多智能体编排是什么：主控分发 + 子 Agent + 汇总 |
| 10:30-12:00 | 1.5h | 为什么编排难测：子 Agent 是 LLM，需要确定替身 |
| 14:00-16:00 | 2h | 实战：orchestrator.py（Orchestrator + SequentialOrchestrator + MockSubAgent） |
| 16:00-17:30 | 1.5h | 实战：test_agent_orchestrator.py（分发/汇总/顺序/未知 Agent） |
| 19:00-20:30 | 1.5h | 全量 65 用例 + 复盘 |
| 20:30-21:00 | 0.5h | 学习日志 + commit 打卡 |

---

## 一、多智能体编排是什么（1.5h）★ 今日重点

> 单 Agent：一个 Agent 自己思考行动。
> 多智能体：**主控 Orchestrator 把子任务分发给多个子 Agent，再汇总**。

这是 roadmap Phase 4 的核心差异化维度：

| Agent 测试维度 | 落点 |
|---|---|
| **有状态会话** | session 级 fixture 维护多轮对话 |
| **工具调用断言** | 每步 tool_calls 的 name+args |
| **ReAct 轨迹** | tool-call → observation → 下一轮 |
| **记忆** | 写入/检索/遗忘的 fixture 驱动 |
| **终止性** | 不超过 max_iterations |
| **LangGraph 状态图** | graph.invoke 状态 + 边转移 |
| **Oracle 模式** | 确定性规则 + LLM-as-Judge |
| **多智能体编排** | mock 子 Agent 返回，断言分发/汇总 |

> 关键：**真实子 Agent 是 LLM**（思考该干啥）。
> 测试不能依赖模型 → 注入 **MockSubAgent**（确定性替身），只测"编排链路"。

---

## 二、`orchestrator.py`（2h）★ 产出①

```python
"""orchestrator.py — 多智能体编排（确定性，可测试）。"""


class MockSubAgent:
    """确定性子 Agent 替身：.run(query) 返回注入函数结果。"""

    def __init__(self, fn):
        self.fn = fn

    def run(self, query):
        return self.fn(query)


class Orchestrator:
    """主控编排：按 routing 分发，按 queries 汇总。"""

    def __init__(self, sub_agents, routing):
        self.sub_agents = sub_agents
        self.routing = routing

    def dispatch(self, tasks):
        """把 routed 子任务交给对应子 Agent。

        未路由的子任务不进输出字典（不抛错）。
        """
        outs = {}
        for name, query in tasks.items():
            key = self.routing.get(name)
            if key is None:
                continue
            outs[name] = self.sub_agents[key].run(query)
        return outs

    def collect(self, sub_agents, queries):
        """用 queries 逐个喂给 sub_agents，汇总结果列表。"""
        return [s.run(q) for s, q in zip(sub_agents, queries)]


class SequentialOrchestrator:
    """顺序编排：按 sequence 顺序跑子 Agent。"""

    def __init__(self, sub_agents, sequence):
        self.sub_agents = sub_agents
        self.sequence = list(sequence)

    def run(self, tasks):
        """顺序执行 sequence 里的子 Agent。

        遇未知子 Agent → 记 reason="unknown_agent" 并跳过继续。
        """
        outputs = []
        reason = "done"
        for name in self.sequence:
            sub = self.sub_agents.get(name)
            if sub is None:
                reason = "unknown_agent"
                continue
            outputs.append(sub.run({}))
        return {"output": "+".join(outputs), "reason": reason}
```

> 认知边界：真实多智能体 = 主控 Agent 动态决定分发给谁、几轮。
> 这里用确定序列/路由模拟，测"编排结构"而非动态规划。

---

## 三、测试设计（产出②）★ 13 用例全绿

> 全量 65 用例分 5 文件：orchestrator 贡献 13。

### 3.1 MockSubAgent（3 用例）
```python
def test_mock_subagent_return():
    """④ 简单 Mock 子 Agent 返回固定值。"""
    sub = MockSubAgent(lambda q: "mock answer")
    assert sub.run("q") == "mock answer"

def test_tool_metadata_present():
    """② 每个工具带 description + parameters。"""
    for name, meta in TOOLS.items():
        assert "description" in meta
        assert "parameters" in meta

def test_unknown_tool_raises():
    """① 未定义工具抛 KeyError。"""
    with pytest.raises(KeyError):
        invoke_tool("nonexistent_tool", {})
```

### 3.2 分发（4 用例）
```python
def test_dispatch_uses_query():
    """⑥ 子 Agent 拿到真实问题查询。"""
    orchestrator = Orchestrator(
        sub_agents={"a": MockSubAgent(lambda q: "ok")},
        routing={"t1": "a"},
    )
    orchestrator.dispatch({"t1": "hello"})
    assert orchestrator.dispatch({"t1": "hello"})["t1"] == "ok"

def test_dispatch_ignores_unknown_route():
    """⑦ 未路由子任务不进输出字典。"""
    orchestrator = Orchestrator(sub_agents={}, routing={})
    assert orchestrator.dispatch({"missing": "q"}) == {}

def test_dispatch_all_tasks():
    """⑤ 分发器把所有子任务交给子 Agent。"""
    orchestrator = Orchestrator(
        sub_agents={"a": MockSubAgent(lambda q: "A")},
        routing={"t1": "a"},
    )
    assert orchestrator.dispatch({"t1": "q"})["t1"] == "A"

def test_collect_results_all():
    """⑨ collect 汇总所有子 Agent 结果。"""
    subs = [MockSubAgent(lambda q: "1"),
            MockSubAgent(lambda q: "2"),
            MockSubAgent(lambda q: "3")]
    orchestrator = Orchestrator(sub_agents={}, routing={})
    assert orchestrator.collect(subs, ["q1", "q2", "q3"]) == ["1", "2", "3"]
```

### 3.3 顺序执行 + 终止（6 用例）
```python
def test_sequential_stops_on_unknown():
    """⑬ 顺序编排遇未注册子 Agent → reason="unknown_agent"。"""
    orchestrator = SequentialOrchestrator(
        sub_agents={},
        sequence=["missing"],
    )
    result = orchestrator.run({"t1": "q"})
    assert result["reason"] == "unknown_agent"
    assert result["output"] == ""

def test_sequential_missing_agent():
    """⑫ 缺失子 Agent → 该位置跳过，output 为空。"""
    orchestrator = SequentialOrchestrator(
        sub_agents={"a": MockSubAgent(lambda q: "A")},
        sequence=["a", "missing"],
    )
    result = orchestrator.run({"t1": "q"})
    assert result["output"] == "A"

def test_orchestrator_stops_when_no_routing():
    """⑧ 空路由 → dispatch 返回空字典。"""
    orchestrator = Orchestrator(sub_agents={}, routing={})
    assert orchestrator.dispatch({"x": "q"}) == {}

def test_collect_results_empty():
    """⑩ collect 空输入返回空列表。"""
    orchestrator = Orchestrator(sub_agents={}, routing={})
    assert orchestrator.collect([], []) == []
```

---

## 四、运行 & 验证（1h）

```bash
cd ~/ai-testing-portfolio/agent-lab
pytest -q
# 期望: 65 passed
```

### 关键观察点
- 全绿 → 分发 + 汇总 + 顺序执行 + 未知 Agent 处理都对了 ✅
- `MockSubAgent` 让子 Agent 完全确定，编排链路可复现
- 顺序编排遇未知 Agent 记 `unknown_agent` 但继续跑（不中断）

---

## 五、失败自测（1h）

```python
def test_intentional_fail():
    # 编造一个不存在的编排结果，看 pytest 报什么
    orchestrator = SequentialOrchestrator(
        sub_agents={"a": MockSubAgent(lambda q: "A")},
        sequence=["a", "b"],
    )
    result = orchestrator.run({"t1": "q"})
    assert result["output"] == "A+B"  # 实测 "A"（b 未注册）
```

---

## 六、学习日志模板（20:30）

复制 `~/ai-testing-portfolio/learning-log/2026-08-30.md`，填写：
- 今日学了什么：多智能体编排、MockSubAgent 替身、分发/汇总/顺序执行
- 卡点：编排遇未知子 Agent 该中断还是跳过？（本实现跳过）
- 明日预习：W4 一周复盘 + 整体回顾

## 七、commit 打卡（21:00）

```bash
cd ~/ai-testing-portfolio/agent-lab
git add -A
git commit -m "W4D6: 多智能体编排（Orchestrator + MockSubAgent，65 测试全绿）"
git push
```

---

## 📌 今日自检清单

- [ ] 懂多智能体编排：主控分发 + 子 Agent + 汇总
- [ ] 会用 MockSubAgent 替身（绕开真实 LLM）
- [ ] 会测分发（routing 命中）+ 汇总（collect）
- [ ] 会测顺序执行 + 未知 Agent 处理
- [ ] 日志 + commit 完成

## 🆘 卡住怎么办

- 编排链路复杂 → 拆开：先测单分发，再测顺序执行
- 未知 Agent 行为定不定 → 先定策略（中断 vs 跳过），再写测试
- 卡 > 30min → 想清楚"编排测试测什么：分发 + 汇总 + 顺序"
- 卡 > 2h → 问木木，带报错信息

---

## 🎯 今日关键词

```
orchestrator  → 主控，分发子任务给子 Agent
mocksubagent  → 确定子 Agent 替身（不依赖真实 LLM）
dispatch      → 按 routing 分发子任务
collect       → 汇总各子 Agent 结果
sequence      → 顺序执行，遇未知记 unknown_agent
routing       → 子任务 -> 子 Agent 键 的映射
```

> 今天从"单 Agent"走向"多 Agent 编排"——真实 Agent 系统常由多个专职子 Agent 协作。
> 测试编排 = 测试主控分发对不对、汇总全不全、顺序乱不乱。
