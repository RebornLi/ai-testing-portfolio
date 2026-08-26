# W4-D3 详细学习内容 · Agent 测试实战：多工具协作 + 工具调用错误断言（6-8 小时版）

> 日期：2026-08-28（周四）｜ 主题：Agent 测试进阶 — 多工具协作 + 错误断言
> 目标：测"一个问题需要多个工具按意图协作" + 工具调用错误（参数/类型/未知）的表现
> 验收：`test_agent_collab.py` 10 用例全绿 + `agent-lab` 42 用例全绿 + 学习日志 + commit

---

## ⏰ 今日时间块（6-8 小时）

| 时间段 | 时长 | 内容 |
|---|---|---|
| 09:00-10:30 | 1.5h | 为什么多工具协作难测（真实规划动态、意图拆分） |
| 10:30-12:00 | 1.5h | 工具调用错误：缺失参数、类型错误、未知工具 |
| 14:00-16:00 | 2h | 实战：test_agent_collab.py（协作链 + 错误断言） |
| 16:00-17:30 | 1.5h | 协作链结果组合：前一步输出=后一步输入 |
| 19:00-20:30 | 1.5h | 运行 + 复盘 |
| 20:30-21:00 | 0.5h | 学习日志 + commit 打卡 |

---

## 一、为什么多工具协作难测（1.5h）★ 今日重点

> 普通测试：一个问题 → 一次工具调用 → 一个结果。
> 协作链：**一个问题 → 多个工具按"意图"协作 → 合成答案**。

Agent 测试要测的协作维度：

| 协作维度 | 落点 |
|---|---|
| **工具去重** | 同一工具多次调用，结果不串 |
| **协作链** | 前一步工具输出 = 后一步工具输入 |
| **意图顺序** | 调用顺序匹配问题意图顺序 |
| **错误表现** | 参数缺失 / 类型错误 / 未知工具时不崩溃 |

> 关键：**真实 Agent 的工具调用顺序来自 LLM 思考**，无法预知。
> 测试注入确定性序列，验证"协作链路"正确、错误时行为可控。

---

## 二、工具调用错误断言（1.5h）

> 工具调用出错时，agent 不该静默失败——要能被断言捕获。

```python
def test_tool_missing_arg_raises():
    """① 缺失必要参数 → 工具抛错（TypeError/KeyError，不是静默）。"""
    with pytest.raises((KeyError, TypeError)):
        invoke_tool("add", {"a": 1})   # 缺 b

def test_tool_type_error_raises():
    """② 参数类型错误 → 工具抛错。"""
    with pytest.raises(TypeError):
        invoke_tool("multiply", {"a": "x", "b": "y"})

def test_lookup_unknown_city():
    """③ 查未知城市 → 返回"天气未知"（已知错误处理）。"""
    assert "天气未知" in invoke_tool("lookup", {"city": "atlantis"})

def test_unknown_tool_error_message():
    """④ 未知工具的错误信息含工具名，便于定位。"""
    with pytest.raises(KeyError) as exc:
        invoke_tool("no_such_tool", {})
    assert "no_such_tool" in str(exc.value)
```

> 观察点：
> - `add` 缺 `b` → KeyError（参数缺失）
> - `multiply` 传字符串 → TypeError
> - 未知工具 → KeyError，错误信息带工具名

---

## 三、多工具协作链（2h）★ 产出①

> 协作链 = 多个工具按意图依次执行，前一步结果注入下一步。

```python
def test_collaboration_two_tools():
    """⑤ 一个任务协作 add + multiply。"""
    agent = ReActAgent(
        DeterministicPlanner([
            ("tool", "add", {"a": 10, "b": 5}),   # 15
            ("tool", "multiply", {"a": 15, "b": 2}),  # 30
            ("answer", "30"),
        ]),
        max_iterations=10,
    )
    res = agent.run("10 加 5 再乘 2")
    names = [c.name for c in res["trajectory"]]
    assert "add" in names and "multiply" in names
    assert res["answer"] == "30"

def test_collaboration_dedup_tools():
    """⑥ 同一工具多次调用 → 去重后仍是预期集合。"""
    chain = agent.run("两地天气")["trajectory"]
    assert {c.name for c in chain} == {"lookup"}
    assert len(chain) == 2

def test_collaboration_result_composition():
    """⑦ 前一步工具结果成为后一步输入（协作链）。"""
    chain = agent.run("6 加 7 再乘 3")["trajectory"]
    assert chain[1].args == {"a": 13, "b": 3}  # a 来自上一步结果
    assert chain[1].result == 39
```

> 关键设计：协作链的正确性 = **后一步工具参数包含前一步的输出**。
> 测试断言 `chain[1].args` 的输入 = `chain[0].result`，这正是 ReAct 状态传播的本质。

---

## 四、工具顺序与错误终止（1.5h）

```python
def test_tool_order_matches_intent():
    """⑧ 工具调用顺序与意图顺序一致。"""
    chain = agent.run("4 乘 5 再加 10")["trajectory"]
    assert [c.name for c in chain] == ["multiply", "add"]

def test_registered_tool_usable():
    """⑩ 注册表里每个工具都能被直接调用。"""
    for name in tool_names():
        assert name in TOOLS
```

> 观察点：
> - 顺序 = 问题意图顺序（"先乘后加"）
> - 注册表与工具实现保持一致

---

## 五、运行 & 验证（1h）

```bash
cd ~/ai-testing-portfolio/agent-lab
pytest -q
# 期望: 42 passed
```

### 关键观察点
- 全绿 → 协作链 + 错误断言 + 顺序都对 ✅
- `missing_arg` → KeyError（缺失参数）
- `type_error` → TypeError（类型不匹配）

---

## 六、失败自测（1h）

```python
def test_intentional_fail():
    # 把协作链答案错写成 31（真实 30），看 pytest 报什么
    agent = ReActAgent(
        DeterministicPlanner([
            ("tool", "add", {"a": 10, "b": 5}),
            ("tool", "multiply", {"a": 15, "b": 2}),
            ("answer", "31"),
        ]),
        max_iterations=10,
    )
    assert agent.run("协作链")["answer"] == "31"  # 实测 == "30"
```

---

## 七、学习日志模板（20:30）

复制 `~/ai-testing-portfolio/learning-log/2026-08-28.md`，填写：
- 今日学了什么：多工具协作链、工具错误断言、意图顺序
- 卡点：工具缺参数时抛什么错（KeyError vs TypeError）
- 明日预习：W4-D4（ReAct 全流程 + 记忆）

## 八、commit 打卡（21:00）

```bash
cd ~/ai-testing-portfolio
git add agent-lab
git commit -m "W4D3: 多工具协作 + 工具调用错误断言（42 测试全绿）"
git push
```

---

## 📌 今日自检清单

- [ ] 懂工具协作链：前一步输出=后一步输入
- [ ] 会测工具错误（缺参/类型/未知）
- [ ] 会测调用顺序（匹配意图）
- [ ] 日志 + commit 完成

## 🆘 卡住怎么办

- 协作链结果不对 → 检查前一步工具输出是否注入后一步参数
- 错误类型不确定 → 用 `pytest.raises((KeyError, TypeError))` 兜底
- 卡 > 30min → 想清楚"工具调用出错时，agent 该怎么处理"
- 卡 > 2h → 问木木，带报错信息

---

## 🎯 今日关键词

```
协作链   → 多工具按意图协作，前一步输出=后一步输入
意图顺序 → 调用顺序匹配问题意图
去重     → 同一工具多次调用不串
错误断言 → 缺参/类型/未知工具都要能断言
replay   → 轨迹自包含，可复现排查
```

> 今天从"单步工具"走向"多工具协作"——这才是真实 Agent 的日常。
> 测协作 = 测链条每一步对不对 + 错误时可控。
