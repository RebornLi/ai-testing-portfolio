# W4-D1 详细学习内容 · Agent 测试实战：ReAct Agent 核心（6-8 小时版）

> 日期：2026-08-26（周二）｜ 主题：Agent 测试入门 — ReAct Agent 核心
> 目标：搭 ReAct Agent + 工具集，用确定性规划器测“轨迹 + 终止 + 状态传播”
> 验收：`agent-lab` 22 用例全绿 + 学习日志 + commit

---

## ⏰ 今日时间块（6-8 小时）

| 时间段 | 时长 | 内容 |
|---|---|---|
| 09:00-10:30 | 1.5h | Agent 测试是什么（vs 普通测试）：有状态会话、轨迹断言、循环 |
| 10:30-12:00 | 1.5h | ReAct 协议：Reasoning + Acting 循环；为什么难测 |
| 14:00-16:00 | 2h | 实战：工具集 tools.py（确定性函数） |
| 16:00-17:30 | 1.5h | 实战：ReActAgent + 注入式规划器（可测性边界） |
| 19:00-20:30 | 1.5h | 测试：test_agent_tools.py（工具正确性+调用链） |
| 20:30-21:00 | 0.5h | 测试：test_agent_core.py（终止+轨迹+状态） |

---

## 一、为什么 Agent 测试特殊（1.5h）★ 今日重点

> 普通 RAG 测试：输入问题 → 答案，单次映射。
> Agent 测试：**多轮、有状态、有副作用**。Agent 自己决定“下一步干什么”。

Agent 测试要测 5 件事（roadmap Phase 4 核心）：

| Agent 测试维度 | 落点 |
|---|---|
| **有状态会话** | 每轮结果注入下一轮（状态传播） |
| **工具调用断言** | 每步 `tool_call` 的 name+args 正确 |
| **ReAct 轨迹** | tool-call → observation → 下一轮 的链式断言 |
| **终止性** | 不超过 max_iterations、不无限循环 |
| **工具正确性** | 工具调用确实被执行、结果正确 |

> 关键：**真实 Agent 的规划器是 LLM**（思考该调哪个工具）。
> 测试不能依赖模型 → 注入**确定性规划器**做替身，只测“执行链路”。

---

## 二、工具集 `tools.py`（1.5h）★ 产出①

> 每个工具 = 纯函数（确定性、可复现）。工具本身无副作用，方便断言。

```python
"""tools.py — Agent 工具集（确定性，可测试）"""

def add(a, b):
    """加法工具：计算 a + b。"""
    return a + b

def multiply(a, b):
    """乘法工具：计算 a * b。"""
    return a * b

def lookup(city):
    """查天气工具：返回某城市天气（mock 返回确定值）。"""
    weather = {
        "beijing": "北京 晴 25°C",
        "shanghai": "上海 多云 28°C",
        "guangzhou": "广州 雨 30°C",
    }
    return weather.get(city.lower(), f"{city} 天气未知")


# 工具注册表：name -> {function, description, parameters}
TOOLS = {
    "add": {"function": add, "description": "计算两数和", "parameters": {"a": "number", "b": "number"}},
    "multiply": {"function": multiply, "description": "计算两数积", "parameters": {"a": "number", "b": "number"}},
    "lookup": {"function": lookup, "description": "查询某城市天气", "parameters": {"city": "string"}},
}

def tool_names():
    """返回所有可用工具名（供规划器参考）。"""
    return sorted(TOOLS.keys())

def invoke_tool(name, args):
    """根据 name 调用对应工具。未定义工具抛 KeyError。"""
    if name not in TOOLS:
        raise KeyError(f"未定义工具: {name}")
    return TOOLS[name]["function"](**args)
```

> ⚠️ **认知边界**：真实工具可能联网/查库（副作用）。纯函数替代保证测试离线、
> 可复现、可断言，但不模拟真实副作用。留待 D2 接真实工具。

---

## 三、ReAct 核心 `agent.py`（2h）★ 产出②

### 3.1 ReAct 是什么
```
每轮：看轨迹 → 规划器决定动作 → 执行工具 → 累积状态 → 重复
终止：给出 answer（正常）或超过 max_iterations（强制）
```

### 3.2 可测性边界：规划器注入
```python
"""agent.py — ReAct Agent 核心（确定性，可测试）"""
from tools import TOOLS, invoke_tool


class ToolCall:
    """一个工具调用步骤。"""
    def __init__(self, name, args, result=None):
        self.name, self.args, self.result = name, args, result


class ReActAgent:
    """ReAct Agent：按规划器动作序列执行，记录轨迹，强制终止。

    planner: callable(history, state) -> {"tool": (name, args)} 或 {"answer": text}
    max_iterations: 硬上限，超过则强终止（防止死循环）。
    """

    def __init__(self, planner, max_iterations=10):
        self.planner = planner
        self.max_iterations = max_iterations

    def run(self, initial_prompt):
        """执行任务，返回 {"answer", "trajectory", "reason": text}。

        reason 三态：
          - "stopped"         规划器给出 answer，正常结束
          - "sequence_end"    确定性序列耗尽仍未 answer
          - "max_iterations"  失控循环，硬上限强终止
        """
        trajectory = []
        state = ""
        for _ in range(self.max_iterations):
            try:
                decision = self.planner(trajectory, state)
            except StopIteration:
                return {"answer": None, "trajectory": trajectory,
                        "reason": "sequence_end"}

            if "answer" in decision:
                return {"answer": decision["answer"],
                        "trajectory": trajectory, "reason": "stopped"}

            name, args = decision["tool"]
            result = invoke_tool(name, args)
            trajectory.append(ToolCall(name, args, result))
            state += f"\n[{name} {args} -> {result}]"

        return {"answer": None, "trajectory": trajectory,
                "reason": "max_iterations"}


class DeterministicPlanner:
    """确定性规划器：按给定固定动作序列执行（测试替身）。"""
    def __init__(self, steps):
        self.steps, self.index = list(steps), 0

    def __call__(self, history, state):
        if self.index >= len(self.steps):
            raise StopIteration
        kind, *rest = self.steps[self.index]
        self.index += 1
        if kind == "tool":
            return {"tool": (rest[0], rest[1])}
        return {"answer": rest[0]}


class LoopingPlanner:
    """失控规划器：永远只发 tool_call、从不给 answer。

    用于测终止性：Agent 必须在 max_iterations 后强终止。
    """
    def __init__(self, name="add", args=None):
        self.name, self.args = name, args or {"a": 1, "b": 1}

    def __call__(self, history, state):
        return {"tool": (self.name, self.args)}
```

### 3.3 设计要点（为什么这样解耦）

| 设计 | 为什么 |
|---|---|
| `planner` 注入 | 测试不依赖 LLM，只测“执行链路” |
| `max_iterations` 硬上限 | 死循环安全，测“终止性” |
| `trajectory` 列表记录 | 每步调用可断言（工具正确性+顺序） |
| `state` 字符串累积 | 每轮结果注入下一轮（状态传播） |

> **卡点解决（D1 实测）**：最初 `DeterministicPlanner` 序列耗尽时抛
> `RuntimeError`，导致 `run()` 也抛错、测试崩。改成 `raise StopIteration`，
> `run()` 捕获后返回 `reason="sequence_end"`。这样“序列用尽”是正常终止态，
> 不是异常。

---

## 四、测试设计（产出③）★ 22 用例全绿

> 全量 22 用例分两文件，全部离线、可复现，不依赖真实模型。

### 4.1 工具集：正确性 + 调用链（`test_agent_tools.py`，10 用例）

```python
def test_add_tool():
    """① add 工具返回两数和。"""
    assert TOOLS["add"]["function"](2, 3) == 5

def test_lookup_tool():
    """③ lookup 返回确定天气。"""
    assert "25" in TOOLS["lookup"]["function"]("beijing")
    assert "天气未知" in TOOLS["lookup"]["function"]("unknowntown")

def test_unknown_tool_raises():
    """⑤ 调用未定义工具抛 KeyError。"""
    with pytest.raises(KeyError):
        invoke_tool("nonexistent_tool", {})

def test_multi_tool_call_chain_order():
    """⑧ 多步工具链按顺序执行。"""
    agent = ReActAgent(
        DeterministicPlanner([
            ("tool", "add", {"a": 3, "b": 4}),   # 7
            ("tool", "multiply", {"a": 7, "b": 2}),  # 14
            ("answer", "14"),
        ]),
        max_iterations=10)
    chain = [(c.name, c.args, c.result) for c in agent.run("算").trajectory]
    assert chain == [
        ("add", {"a": 3, "b": 4}, 7),
        ("multiply", {"a": 7, "b": 2}, 14)]
```

### 4.2 ReAct 核心：终止 + 轨迹 + 状态（`test_agent_core.py`，12 用例）

```python
def test_reason_stopped():
    """① 序列给出 answer → reason="stopped"。"""
    agent = ReActAgent(DeterministicPlanner(
        [("tool", "add", {"a": 1, "b": 1}), ("answer", "2")]),
        max_iterations=10)
    assert agent.run("1+1")["reason"] == "stopped"

def test_reason_max_iterations():
    """③ 失控循环 → reason="max_iterations"。"""
    agent = ReActAgent(LoopingPlanner(), max_iterations=5)
    assert agent.run("循环")["reason"] == "max_iterations"

def test_termination_bounded():
    """④ 失控规划器轨迹长度封顶为 max_iterations（不死循环）。"""
    agent = ReActAgent(LoopingPlanner(), max_iterations=7)
    assert len(agent.run("循环").trajectory) == 7

def test_state_accumulates_across_rounds():
    """⑩ 每轮把上一步结果注入 state，后续轮次可见。"""
    class RecorderPlanner:
        round = 0
        def __call__(self, history, state):
            self.round += 1
            if self.round == 1:
                return {"tool": ("add", {"a": 2, "b": 3})}
            assert "5" in state       # 上一步结果
            return {"answer": "5"}
    agent = ReActAgent(RecorderPlanner(), max_iterations=10)
    assert agent.run("2+3")["answer"] == "5"
```

---

## 五、运行 & 验证（1h）

```bash
cd ~/ai-testing-portfolio/agent-lab
pytest -q
# 期望: 22 passed
```

### 关键观察点
- 全绿 → 工具正确性 + 调用链 + 终止性 + 状态传播都对 ✅
- `test_termination_bounded` → 死循环被 `max_iterations` 硬封顶，不会卡死
- `test_state_accumulates_across_rounds` → 每轮结果确实注入下一轮

---

## 六、学习日志模板（20:30）

复制 `~/ai-testing-portfolio/learning-log/2026-08-26.md`，填写：
- 今日学了什么：ReAct 协议、工具注入、确定性规划器、终止三态
- 卡点：`DeterministicPlanner` 序列耗尽时不应抛 RuntimeError
- 明日预习：W4-D2（工具调用链断言 + ReAct 全流程）

## 七、commit 打卡（21:00）

```bash
cd ~/ai-testing-portfolio
git add agent-lab
git commit -m "W4D1: ReAct Agent 核心 + 工具集（确定性规划器，22 测试全绿）"
git push
```

---

## 📌 今日自检清单

- [ ] 懂 ReAct 协议（Reasoning + Acting 循环）
- [ ] 会用注入式确定性规划器（绕开真实 LLM）
- [ ] 测了工具正确性 + 调用链
- [ ] 测了终止性（max_iterations 强封顶）
- [ ] 测了状态传播（state 累积）
- [ ] 日志 + commit 完成

## 🆘 卡住怎么办

- 序列耗尽报错 → 改用 StopIteration + reason="sequence_end"
- 测试依赖模型 → 用确定性规划器替身，不加载真实模型
- 卡 > 30min → 想清楚“Agent 测试要测什么：轨迹+终止+工具+状态”
- 卡 > 2h → 问木木，带报错信息

---

## 🎯 今日关键词

```
ReAct  → Reasoning + Acting 循环
planner → 规划器（决定下一步动作）；确定性规划器=测试替身
trajectory → 每步 tool_call 记录（可断言）
max_iterations → 硬上限，测终止性/防死循环
state → 每轮累积的观察，注入下一轮
reason 三态 → stopped / sequence_end / max_iterations
```

> 今天给 Agent 装了确定性骨架：真实 Agent 的“思考”由 LLM 决定，
> 但“执行链路”是确定的——这恰恰是可测的部分。
> 测 Agent，先测它不会失控、会终止、会记录轨迹。
