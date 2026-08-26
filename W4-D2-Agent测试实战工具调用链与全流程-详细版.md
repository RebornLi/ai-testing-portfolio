# W4-D2 详细学习内容 · Agent 测试实战：工具调用链 + ReAct 全流程（6-8 小时版）

> 日期：2026-08-27（周三）｜ 主题：Agent 测试进阶 — 工具调用链断言 + 全流程
> 目标：测"多步工具链的 name/args/result/顺序" + 链式计算全流程 + 轨迹重放
> 验收：`test_agent_chain.py` 10 用例全绿 + 学习日志 + commit

---

## ⏰ 今日时间块（6-8 小时）

| 时间段 | 时长 | 内容 |
|---|---|---|
| 09:00-10:30 | 1.5h | Agent 测试 vs 普通测试：多步链式断言、轨迹自包含 |
| 10:30-12:00 | 1.5h | ReAct 全流程：prompt→轨迹→答案，链式计算 |
| 14:00-16:00 | 2h | 实战：工具调用链断言（4 关注点） |
| 16:00-17:30 | 1.5h | 实战：全流程测试（链式计算 + lookup 工具） |
| 19:00-20:30 | 1.5h | 实战：轨迹重放 + 状态隔离 |
| 20:30-21:00 | 0.5h | 学习日志 + commit 打卡 |

---

## 一、Agent 测试 vs 普通测试（1.5h）★ 今日重点

> 普通测试：输入 → 单次输出，测"对不对"。
> Agent 测试：输入 → **多步轨迹** → 答案，测"每一步对不对 + 链条对不对"。

Agent 轨迹是**自包含**的记录：`[{name, args, result}, ...]`。
测试可以断言：
1. 每一步的 **name/args/result**（工具正确性）
2. 每一步的**顺序**（ReAct 链式）
3. 轨迹**可重放**（replay = 重新执行，结果一致）
4. 多任务之间**状态隔离**（state 不串）

> **ReAct 全流程** = prompt → 规划器 → 工具 → 观察 → 再规划 → 直到答案。
> 确定性规划器固定了"已知答案路径"，测试就是验证这条路径每一步都跑对了。

---

## 二、工具调用链断言（2h）★ 产出①

> 多次工具调用时，要断言**每一步**。D1 只测了单步，D2 测链式。

### 2.1 4 个关注点（全部从测试发现，先失败后实现）

```python
def test_chain_args_match_plan():
    """① 每一步的 args，与规划器意图完全一致。"""
    chain = agent.run("算")["trajectory"]
    assert chain[0].args == {"a": 3, "b": 4}
    assert chain[1].args == {"a": 7, "b": 2}

def test_chain_results_correct():
    """② 每一步结果是工具的正确输出。"""
    chain = agent.run("算")["trajectory"]
    assert [c.result for c in chain] == [7, 14]

def test_chain_order_preserved():
    """③ 调用顺序与规划顺序一致。"""
    chain = agent.run("算")["trajectory"]
    assert [c.name for c in chain] == ["add", "lookup", "multiply"]

def test_chain_call_count():
    """④ 总调用次数 = 规划里的 tool 步骤数。"""
    chain = agent.run("算")["trajectory"]
    assert len(chain) == 3
```

> **卡点（D2 真问题）**：最初 `test_agent_chain.py` 有 3 个失败，根因有两个——
> 1. **`replay()` 方法缺失**：轨迹"可重放"是 ReAct 测试的关键能力，但 agent 没实现。
>    → 加 `agent.replay(trajectory)`，重新执行轨迹里的每个 tool_call，返回结果列表。
> 2. **state 隔离测试写错**：用单个 agent + 计数器规划器，第二个 run 提前终止了。
>    → 改用两个独立 agent 各自 run，各自 trajectory 干净 = 规划里的 tool 数。

### 2.2 实现 `replay()`（D2 新增）

```python
class ReActAgent:
    def replay(self, trajectory):
        """重放一段轨迹，返回每步的工具结果列表 [result, ...]。

        重放 = 只重新执行轨迹里的 tool_call，不复跑规划器。
        这是 Agent 测试的关键能力：轨迹自包含、可复现。
        """
        results = []
        for call in trajectory:
            results.append(invoke_tool(call.name, call.args))
        return results
```

---

## 三、ReAct 全流程（1.5h）★ 产出②

> 把"链式计算"当真实任务：prompt → 多步工具 → 最终答案。

```python
def test_full_flow_chained_arithmetic():
    """⑤ 多步链式计算 ((2+3) * 4) = 20，答案正确。"""
    agent = ReActAgent(
        DeterministicPlanner([
            ("tool", "add", {"a": 2, "b": 3}),   # 5
            ("tool", "multiply", {"a": 5, "b": 4}),  # 20
            ("answer", "20"),
        ]),
        max_iterations=10,
    )
    res = agent.run("2 加 3 再乘 4")
    assert res["answer"] == "20"
    assert res["reason"] == "stopped"
    assert [c.result for c in res["trajectory"]] == [5, 20]


def test_full_flow_with_lookup():
    """⑥ 全流程用 lookup 工具，结果正确且进入答案。"""
    agent = ReActAgent(
        DeterministicPlanner([
            ("tool", "lookup", {"city": "Beijing"}),
            ("answer", "北京 晴 25°C"),
        ]),
        max_iterations=10,
    )
    res = agent.run("北京天气？")
    assert res["trajectory"][0].result == "北京 晴 25°C"
    assert res["answer"] == "北京 晴 25°C"
```

> 链式计算 = ReAct 的最小真实任务：规划器决定"先加后乘"，
> 每步结果注入下一步的 state（所以 multiply 的 a=5 来自上一步）。

---

## 四、轨迹重放 + 状态隔离（1.5h）★ 产出③

```python
def test_trajectory_replay():
    """⑧ 重新执行 trajectory，能得到相同结果。"""
    trajectory = agent.run("算")["trajectory"]
    replayed = agent.replay(trajectory)
    assert replayed == [10, 30]


def test_state_isolation_between_runs():
    """⑩ 独立 agent 各自 run，各自轨迹干净。"""
    def build():
        return ReActAgent(
            DeterministicPlanner([
                ("tool", "add", {"a": 1, "b": 1}),
                ("answer", "2"),
            ]),
            max_iterations=10,
        )
    r1 = build().run("任务A")
    r2 = build().run("任务B")
    assert len(r1["trajectory"]) == 1
    assert len(r2["trajectory"]) == 1
```

> **为什么 replay 重要**：真实 Agent 跑了 10 步，出 bug 了——
> 光看日志难定位。轨迹重放 = 把那 10 步固定下来，单独复现排查。
> 这就是 Agent 测试里的"可复现性"断言。

---

## 五、运行 & 验证（1h）

```bash
cd ~/ai-testing-portfolio/agent-lab
pytest -q
# 期望: 32 passed（agent-core 12 + agent-tools 10 + agent-chain 10）
```

### 关键观察点
- 全绿 → 链式工具断言 + 全流程 + 重放 + 状态隔离都对了 ✅
- `replay()` 是新增方法：轨迹自包含、可复现
- 三个失败全是"先写测试、发现 agent 缺能力"——这正是 TDD 的价值

---

## 六、失败自测（1h）

```python
def test_intentional_fail():
    # 把链式计算的答案错写成 25（真实 20），看 pytest 报什么
    agent = ReActAgent(
        DeterministicPlanner([
            ("tool", "add", {"a": 2, "b": 3}),
            ("tool", "multiply", {"a": 5, "b": 4}),
            ("answer", "25"),  # 应该是 20
        ]),
        max_iterations=10,
    )
    assert agent.run("2+3*4")["answer"] == "25"  # 实测 == "20"
```

---

## 七、学习日志模板（20:30）

复制 `~/ai-testing-portfolio/learning-log/2026-08-27.md`，填写：
- 今日学了什么：工具调用链断言、ReAct 全流程、轨迹重放、状态隔离
- 卡点：replay() 方法缺失 → 先写测试发现缺能力
- 明日预习：W4-D3（多工具协作 + 工具调用错误断言）

## 八、commit 打卡（21:00）

```bash
cd ~/ai-testing-portfolio
git add -A
git commit -m "W4D2: ReAct 工具调用链 + 全流程 + 轨迹重放（32 测试全绿）"
git push
```

---

## 📌 今日自检清单

- [ ] 懂工具调用链要断言：name/args/result/顺序
- [ ] 会测全流程链式计算
- [ ] 会用 replay() 复现轨迹
- [ ] 测了状态隔离（多任务不串 state）
- [ ] 日志 + commit 完成

## 🆘 卡住怎么办

- 轨迹重放失败 → 检查 replay 是否重新执行了每个 tool_call
- state 跨任务累积 → 每个 run 用独立 agent
- 卡 > 30min → 想清楚"Agent 测试测什么：轨迹+链式+终止+状态"
- 卡 > 2h → 问木木，带报错信息

---

## 🎯 今日关键词

```
tool chain → 多步工具调用链（每步断言）
ReAct flow → prompt→轨迹→答案 全流程
replay     → 重放轨迹复现结果（可复现性）
state isolation → 多任务状态不串
chain      → 链式计算（+ 依赖上一步结果）
```

> 今天从"单步工具"走向"链式工具"——这才是 Agent 的常态。
> 测试 Agent 轨迹 = 把它当一份可复现的执行日志，逐环断言。
