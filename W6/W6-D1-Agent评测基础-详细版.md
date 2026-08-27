# W6-D1 详细学习内容 · Agent 评测基础：四维度评分框架（6-8 小时版）

> 日期：2026-09-04（周五）｜ 主题：Agent 评测 —— 为什么给 Agent 打分比"问答对错"难
> 目标：建立 Agent 评测四维度框架（任务规划 / 工具调用 / 多轮上下文 / 记忆管理），能讲清"怎么评价一个 Agent"
> 验收：评测四维度表 + 给确定性 Agent 手算得分 + 概念笔记 + commit

---

## ⏰ 今日时间块（6-8 小时）

| 时间段 | 时长 | 内容 |
|---|---|---|
| 09:00-10:30 | 1.5h | 为什么 Agent 评测更难：不只是"对错"，而是"过程对不对" |
| 10:30-12:00 | 1.5h | 四维度框架：任务规划 / 工具调用 / 多轮上下文 / 记忆管理 |
| 14:00-16:00 | 2h | 实战：给一个确定性 Agent 跑任务，手算四维度得分 |
| 16:00-17:30 | 1.5h | 实战：设计"故意失败"的任务，验证评测框架能抓出来 |
| 19:00-20:30 | 1.5h | 概念笔记① 落盘（四维度表 + 评分规则） |
| 20:30-21:00 | 0.5h | 一句话笔记 + 学习日志 + commit |

---

## 一、为什么 Agent 评测比"问答对错"难（1.5h）★ 今日重点

> 一句话：**普通问答只问"答案对不对"；Agent 还要问"它做事的过程对不对"。**

### 普通问答 vs Agent 评测

| | 普通问答 | Agent |
|---|---|---|
| 判断标准 | 答案对不对 | 答案对不对 + 过程对不对 |
| 输入 | 一个问题 | 一个目标 + 一堆可选工具 |
| 输出 | 一段文本 | 一串动作（工具调用）+ 最终答案 |
| 失败类型 | 答案错 | 工具用错 / 顺序错 / 忘了上下文 / 忘事 |

> **Agent = 会动手的 AI**：它能调用工具（搜索、计算、查数据库）。评测它不仅看最后的答案，还要看：
> - 它该用什么工具？用的对吗？
> - 调用顺序合理吗？
> - 多轮对话时，它还记得前面聊过什么吗？

### Agent 的四维度（评测框架）

| 维度 | 看什么 | 大白话 |
|---|---|---|
| **① 任务规划** | 是否朝着目标一步步来 | "有没有按套路出牌" |
| **② 工具调用** | 每个工具的参数、顺序、结果对不对 | "工具用对了没" |
| **③ 多轮上下文** | 是否记得上一轮说了什么 | "会不会'忘事'" |
| **④ 记忆管理** | 是否把重要信息存下来复用 | "小本本记了没" |

> 记忆口诀：**规划、调用、上下文、记忆**——这就是 Agent 评测的四根柱子。

---

## 二、四维度详解 + 怎么打分（1.5h）★ 核心

> 每个维度给一个"任务完成率"（0~100%），凑成整体评分。

### ① 任务规划（Task Planning）
- 看 Agent 的动作序列是否朝向目标。
- 打分：正确步骤数 / 必要步骤数。
- 反例：要"算总价"，它却去"查天气"——规划跑偏。

### ② 工具调用（Tool Calling）★ 今日最该理解
- 看每个 `tool_call` 的 **name + 参数 + 结果**。
- 打分点：
  - 用了正确的工具名吗？（该 `add` 没去 `weather`）
  - 参数对吗？（该传 `{"a":3,"b":4}` 没传错）
  - 调用顺序对吗？（先加后乘）
  - 结果对吗？（工具返回正确）

### ③ 多轮上下文（Multi-turn Context）
- 用户多轮说话，Agent 要"记得上一轮"。
- 反例：用户说"我叫小明，帮我算 3+4"，Agent 回答数字却忘了自己叫什么。

### ④ 记忆管理（Memory）
- Agent 是否把关键信息写进长期记忆（小本本），后续回合复用。
- 反例：每轮都让用户"重新说一遍名字"。

---

## 三、实战：给确定性 Agent 跑任务（2h）★ 产出①

> 用一个和 W4 结构一致的确定性 Agent（ReAct）。它会按固定序列调工具，我们评测它。

### 3.1 Agent 长这样（确定性，可复现）

```python
"""W6-D1 评测对象：确定性 ReAct Agent（对齐 W4 结构）"""
from tools import TOOLS, invoke_tool


class ToolCall:
    """一个工具调用步骤：工具名 + 参数 + 结果。"""
    def __init__(self, name, args, result=None):
        self.name, self.args, self.result = name, args, result


class ReActAgent:
    """按固定动作序列执行，记录轨迹，强制终止。"""
    def __init__(self, planner, max_iterations=10):
        self.planner, self.max_iterations = planner, max_iterations

    def run(self, initial_prompt):
        trajectory, state = [], ""
        for _ in range(self.max_iterations):
            decision = self.planner(trajectory, state)     # 规划器出动作
            if "answer" in decision:                       # 给答案 → 正常结束
                return {"answer": decision["answer"], "trajectory": trajectory, "reason": "stopped"}
            name, args = decision["tool"]                  # 否则调工具
            result = invoke_tool(name, args)
            trajectory.append(ToolCall(name, args, result))
            state += f"\n[{name} {args} -> {result}]"
        return {"answer": None, "trajectory": trajectory, "reason": "max_iterations"}


class DeterministicPlanner:
    """确定性规划器：按固定步骤走（测试用）。"""
    def __init__(self, steps):
        self.steps, self.i = list(steps), 0

    def __call__(self, history, state):
        if self.i >= len(self.steps):
            raise StopIteration
        kind, *rest = self.steps[self.i]; self.i += 1
        if kind == "tool":
            return {"tool": (rest[0], rest[1])}
        return {"answer": rest[0]}
```

### 3.2 工具集（和 W4 一致）

```python
"""W6-D1 评测用工具集（确定性，不依赖真实服务）"""
TOOLS = {"add", "lookup", "multiply", "weather"}


def invoke_tool(name, args):
    if name == "add":
        return args["a"] + args["b"]
    if name == "multiply":
        return args["a"] * args["b"]
    if name == "lookup":
        db = {"beijing": "晴天", "atlantis": "未知"}
        return db.get(args["city"], "未知城市")
    if name == "weather":
        return "晴天 25°C"
    raise ValueError(f"未知工具：{name}")
```

### 3.3 跑一个任务，看它的动作

```python
"""W6-D1 任务：先算 3+4，再乘 2，最后给答案"""
plan = DeterministicPlanner([
    ("tool", "add", {"a": 3, "b": 4}),   # 步骤1
    ("tool", "multiply", {"a": 7, "b": 2}),  # 步骤2
    ("answer", "结果是14"),                # 步骤3
])

agent = ReActAgent(plan)
res = agent.run("完成任务")
trajectories = res["trajectory"]

for c in trajectories:
    print(f"{c.name} | args={c.args} | result={c.result}")
```

**期望**：三条轨迹——`add→multiply→answer`，结果分别是 7、14、"结果是14"。

---

## 四、给这个 Agent 打四维度分（1.5h）★ 产出

> 任务设计：先加后乘（正确顺序），最终答案 14。我们逐维度打分。

```python
"""W6-D1 给 Agent 轨迹打四维度分（重新建一个好 agent 来评）"""
good_plan = DeterministicPlanner([
    ("tool", "add", {"a": 3, "b": 4}),
    ("tool", "multiply", {"a": 7, "b": 2}),
    ("answer", "结果是14"),
])
agent = ReActAgent(good_plan)
res = agent.run("完成任务")
traj = res["trajectory"]
answer = res["answer"]

# 必要步骤（设计目标）：add → multiply → answer
necessary = ["add", "multiply", "answer"]

# ① 任务规划：实际调用的工具名，是否在必要序列里
plan_ok = all(c.name in ["add", "multiply"] for c in traj)
# ② 工具调用：每步参数对不对、结果对不对
tool_ok = (traj[0].args == {"a": 3, "b": 4} and traj[1].args == {"a": 7, "b": 2})
# ③ 结果正确
result_ok = (traj[0].result == 7 and traj[1].result == 14 and answer == "结果是14")
# ④ 记忆：这里没有多轮，先看是否"回答了问题"
memory_ok = bool(answer)

score = {"任务规划": plan_ok, "工具调用": tool_ok, "结果正确": result_ok, "回答": memory_ok}
print("四维度得分:", score)
print(f"综合完成率 = {sum(score.values()) / len(score) * 100:.0f}%")
```

**期望**：全部 True，综合 100%。

### 反过来：设计一个"坏 Agent"，评测要能抓出来

```python
"""坏 Agent：工具顺序错了（先乘后加）→ 四维度要扣分"""
bad_plan = DeterministicPlanner([
    ("tool", "multiply", {"a": 7, "b": 2}),   # 顺序错了！
    ("tool", "add", {"a": 1, "b": 1}),         # 多余的步骤
    ("answer", "错误答案"),
])
bad = ReActAgent(bad_plan)
bad_res = bad.run("完成任务")
bt = bad_res["trajectory"]
print("坏Agent工具名顺序:", [c.name for c in bt])   # 应看出异常
```

> 观察：好 Agent 轨迹是 `add→multiply`，坏 Agent 是 `multiply→add`——**评测框架要能把这种"顺序错"抓出来。**

---

## 五、概念笔记① 落盘（1.5h）★ 产出

> 一句话记忆点：

1. **Agent 评测更难**：不止看答案对错，还要看"做事的过程对不对"。
2. **四维度**：任务规划 / 工具调用 / 多轮上下文 / 记忆管理。
3. **工具调用是最细的维度**：每一步的 name、参数、顺序、结果都要断言。
4. **打分方式**：每个维度算"任务完成率"，再综合成总体分。
5. **评测要能抓坏例子**：设计故意失败的 Agent，验证框架会扣分。
6. **轨迹是关键**：Agent 的 `trajectory`（动作记录）是评测的"证据"。

---

## 六、面试口述版（大白话，别背术语）

> 普通问答测试像"看学生答案对不对"。Agent 测试像"看学生解题步骤对不对"——
> 他最终答案对了，但你可能用错了公式、抄错了数。所以要看他每一步怎么做的。
> 看四件事：他有没有按套路来（规划）、工具用得对不对（调用）、
> 记不记得上一轮说了什么（上下文）、重不重用小本本（记忆）。

---

## ⏰ 今日验收清单

- [ ] 能讲清"Agent 评测为什么比问答难"
- [ ] 能说出四维度各看什么
- [ ] 给确定性 Agent 跑通任务，四维度分都拿到了
- [ ] 坏 Agent 的错能被评测框架抓出来
- [ ] 概念笔记① 落盘
- [ ] 学习日志写了（含卡点）
- [ ] 已 commit

## ⏰ 卡点提示

- 怎么判定"顺序错"？对比 Agent 实际轨迹顺序 vs 正确任务顺序。
- 四维度权重怎么分？默认等权；真实项目可按任务调整（如工具调用更重要）。

## 📝 学习日志

> 今天（09-04 周五）：
> 1. 学 Agent 评测：不止看答案，要看做事过程。
> 2. 建了四维度框架：任务规划 / 工具调用 / 多轮上下文 / 记忆管理。
> 3. 用确定性 Agent 跑"先加后乘"任务，四维度分都 100%。
> 4. 坏 Agent（先乘后加）轨迹是 multiply→add，评测能抓出来。
> 5. 卡点：工具调用维度最细，每步参数、顺序、结果都要断言。
> 6. 明天 D2 专门练工具调用断言（多步链式）。

---
*创建于 W6-D1 · 计划：AI 求职阶段二 W6 第 6 周*
