# W4-D4 详细学习内容 · Agent 测试实战：ReAct 全流程 + 记忆系统（6-8 小时版）

> 日期：2026-08-29（周五）｜ 主题：Agent 测试进阶 — 多轮全流程 + 记忆
> 目标：测"记忆系统"（写/检索/遗忘/容量）+ 记忆驱动行为
> 验收：`agent.py` 加 `Memory`、`test_agent_memory.py` 10 用例全绿 + `agent-lab` 52 全绿 + 学习日志 + commit

---

## ⏰ 今日时间块（6-8 小时）

| 时间段 | 时长 | 内容 |
|---|---|---|
| 09:00-10:30 | 1.5h | 记忆是什么：写/检索/遗忘/容量上限 |
| 10:30-12:00 | 1.5h | 记忆如何影响 Agent 行为（多轮决策） |
| 14:00-16:00 | 2h | 实战：agent.py 加 Memory 类 |
| 16:00-17:30 | 1.5h | 实战：test_agent_memory.py（写/检索/遗忘/容量） |
| 19:00-20:30 | 1.5h | 记忆驱动行为 + 全流程验证 |
| 20:30-21:00 | 0.5h | 学习日志 + commit 打卡 |

---

## 一、记忆是什么（1.5h）★ 今日重点

> 普通 Agent：无状态，每轮只看轨迹。
> 有记忆 Agent：**之前做的事会"记住"，影响后面**。

记忆四件事：

| 记忆操作 | 落点 |
|---|---|
| **写** | 把观察/结果存起来 |
| **检索** | 后续任务读到已写内容 |
| **遗忘** | 主动删除记忆条目 |
| **容量** | 超过上限时的行为（覆盖/拒绝） |

> 关键：记忆 = Agent 的"长期上下文"。真实 Agent 有上下文窗口限制，
> 记忆系统就是解决"记多少、记什么、用不用的到"。

---

## 二、记忆系统 `agent.py`（2h）★ 产出①

```python
class MemoryFull(Exception):
    """记忆满（超出容量）时抛出。"""
    pass


class Memory:
    """简单键值记忆 + 容量上限（测试用）。

    认知边界：真实 Agent 的记忆 = 长期上下文 / 外部存储，容量无限。
    这里用固定容量字典模拟，测"写/检索/遗忘/容量上限"行为。
    """

    def __init__(self, capacity=10):
        self.data = {}
        self.capacity = capacity

    def write(self, key, value):
        if len(self.data) >= self.capacity and key not in self.data:
            raise MemoryFull()
        self.data[key] = value

    def retrieve(self, key):
        return self.data.get(key)

    def forget(self, key):
        self.data.pop(key, None)

    def clear(self):
        self.data.clear()
```

> 观察点：
> - `write` 满容量抛 `MemoryFull`
> - `retrieve` 不存在键 → None
> - `forget` 不存在的键也不报错（pop + 默认 None）

---

## 三、记忆系统测试（1.5h）★ 10 用例全绿

```python
def test_memory_write_retrieve():
    """① 写记忆后能检索到对应值。"""
    mem = Memory()
    mem.write("city", "beijing")
    assert mem.retrieve("city") == "beijing"

def test_memory_missing_key_returns_none():
    """② 检索不存在的键 → 返回 None。"""
    mem = Memory()
    assert mem.retrieve("nonexistent") is None

def test_memory_capacity_overflow():
    """⑤ 超过容量上限写新键 → 抛 MemoryFull。"""
    mem = Memory(capacity=2)
    mem.write("a", 1)
    mem.write("b", 2)
    with pytest.raises(MemoryFull):
        mem.write("c", 3)
```

> 观察点：
> - 容量=2 时第 3 个键被拒绝
> - 覆盖已存在键不算新写入（不抛 MemoryFull）

---

## 四、记忆驱动行为（1.5h）★ 产出②

```python
def test_memory_drives_behavior():
    """⑦ 有记忆 vs 无记忆，agent 行为不同。"""
    # 有记忆：第二轮从记忆取到值
    mem = Memory()
    mem.write("cached", "hello")

    class WithMemPlanner:
        round = 0
        def __call__(self, history, state):
            self.round += 1
            if self.round == 1:
                return {"tool": ("lookup", {"city": "shanghai"})}
            return {"answer": mem.retrieve("cached")}

    res = ReActAgent(WithMemPlanner(), max_iterations=10).run("有记忆")
    assert res["answer"] == "hello"

    # 无记忆：第二轮检索到 None
    class NoMemPlanner:
        round = 0
        def __call__(self, history, state):
            self.round += 1
            if self.round == 1:
                return {"tool": ("lookup", {"city": "shanghai"})}
            return {"answer": Memory().retrieve("cached")}

    res2 = ReActAgent(NoMemPlanner(), max_iterations=10).run("无记忆")
    assert res2["answer"] is None
```

> 关键设计：记忆写进写出 Agent 外（`Memory` 对象），
> 规划器在第二轮 `retrieve`。这正是 ReAct 状态传播的延伸——
> 从"状态字符串"升级到"持久记忆"。

---

## 五、运行 & 验证（1h）

```bash
cd ~/ai-testing-portfolio/agent-lab
pytest -q
# 期望: 52 passed（D1:32 工具+链, D2 扩展, D3 协作, D4 记忆 10）
```

### 关键观察点
- 全绿 → 记忆四操作 + 驱动行为都对 ✅
- `MemoryFull` 在容量=2 时触发第 3 次 write
- 有记忆 agent 拿到缓存，无记忆 agent 拿到 None

---

## 六、失败自测（1h）

```python
def test_intentional_fail():
    # 检索不存在的键，错写成不返回 None，看 pytest 报什么
    mem = Memory()
    assert mem.retrieve("no_key") == "default"  # 实测 None
```

---

## 七、学习日志模板（20:30）

复制 `~/ai-testing-portfolio/learning-log/2026-08-29.md`，填写：
- 今日学了什么：记忆四操作、容量上限、记忆驱动行为
- 卡点：记忆满时该抛错还是覆盖？
- 明日预习：W4-D5（ReAct 全流程收尾 + 一周复盘）

## 八、commit 打卡（21:00）

```bash
cd ~/ai-testing-portfolio
git add agent-lab
git commit -m "W4D4: ReAct 全流程 + 记忆系统（52 测试全绿）"
git push
```

---

## 📌 今日自检清单

- [ ] 懂记忆四操作（写/检索/遗忘/容量）
- [ ] 会测 MemoryFull（容量超限）
- [ ] 会测记忆驱动行为（有记忆 vs 无记忆）
- [ ] 日志 + commit 完成

## 🆘 卡住怎么办

- 记忆检索失败 → 检查 key 是否写错、是否跨实例隔离
- 满容量行为不清 → 先确定"抛错 vs 覆盖"策略
- 卡 > 30min → 想清楚"记忆 Agent vs 无记忆 Agent 差在哪"
- 卡 > 2h → 问木木，带报错信息

---

## 🎯 今日关键词

```
Memory → 键值记忆 + 容量上限
write  → 写记忆（满抛 MemoryFull）
retrieve → 检索（不存在→None）
forget → 遗忘（pop + 默认 None）
capacity → 容量上限（覆盖已存在键不算新写入）
memory-driven → 记忆决定行为
```

> 今天从"轨迹"走向"记忆"——Agent 不再失忆。
> 测记忆 = 测写得到、查得到、忘得掉、有上限。
