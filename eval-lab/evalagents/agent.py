"""eval_lab/agent.py — 确定性 ReAct Agent 家族（对齐 W6-D1/D3/D4）。

一个 agent 跑完任务，返回 {answer, trajectory, reason}。
trajectory 是每个 ToolCall 的列表（"answer" 是终态决策，不进轨迹）。

★ 关键教训（笔记反复踩的坑）：
    DeterministicPlanner 是【有状态】的，run 一次就耗尽。
    每次 run 都要【重新构建】规划器/agent，否则第二次复用旧的会
    raise StopIteration（序列已到头）或 memory 状态串台。
"""
import time
from evalagents.tools import invoke_tool


class ToolCall:
    """一个工具调用步骤：工具名 + 参数 + 结果。"""
    def __init__(self, name, args, result=None):
        self.name = name
        self.args = args
        self.result = result


# ---------- 规划器 ----------

class DeterministicPlanner:
    """按固定步骤序列跑（确定性，测专用）。

    步骤元组：
        ("tool", name, args)   -> 调用工具
        ("answer", text)       -> 终态，给出答案
    """
    def __init__(self, steps):
        self.steps, self.i = list(steps), 0

    def __call__(self, trajectory, state):
        if self.i >= len(self.steps):
            raise StopIteration
        kind, *rest = self.steps[self.i]
        self.i += 1
        if kind == "tool":
            return {"tool": (rest[0], rest[1])}
        return {"answer": rest[0]}


class LoopingPlanner:
    """失控规划器：永远只发工具、永远不 answer（用于测 max_iterations）。"""
    def __call__(self, trajectory, state):
        return {"tool": ("add", {"a": 1, "b": 1})}


# ---------- Agent ----------

class ReActAgent:
    """按固定动作序列执行，记录轨迹，可重放。"""
    def __init__(self, planner, max_iterations=10):
        self.planner = planner
        self.max_iterations = max_iterations

    def run(self, initial_prompt):
        trajectory, state = [], ""
        for _ in range(self.max_iterations):
            decision = self.planner(trajectory, state)
            if "answer" in decision:
                return {"answer": decision["answer"],
                        "trajectory": trajectory, "reason": "stopped"}
            name, args = decision["tool"]
            result = invoke_tool(name, args)
            trajectory.append(ToolCall(name, args, result))
            state += f"\n[{name} {args} -> {result}]"
        return {"answer": None, "trajectory": trajectory,
                "reason": "max_iterations"}

    def replay(self, trajectory):
        """重放轨迹，返回每步结果列表。"""
        return [invoke_tool(c.name, c.args) for c in trajectory]


class Memory:
    """简单 dict 记忆：写 / 读 / 清空。"""
    def __init__(self):
        self.store = {}

    def write(self, key, value):
        self.store[key] = value
        return True

    def read(self, key):
        return self.store.get(key)

    def clear(self):
        self.store.clear()
        return True


class MemoryAgent:
    """带 Memory 的 Agent：多轮对话中把关键信息写进小本本复用。

    规划器能拿到 self.memory。多轮必须共用【同一个 agent】（或至少同一个
    memory），否则跨轮 memory 不共享，表现成"忘事"。
    """
    def __init__(self, planner, memory=None, max_iterations=10):
        self.planner = planner
        self.memory = memory or Memory()
        self.max_iterations = max_iterations
        self.last_answer = None  # 记录最近一轮答案，供评测读取（不重跑 agent）

    def run(self, prompt):
        trajectory, state = [], ""
        for _ in range(self.max_iterations):
            decision = self.planner(prompt, trajectory, state, self.memory)
            if "answer" in decision:
                self.last_answer = decision["answer"]
                return {"answer": decision["answer"],
                        "trajectory": trajectory, "reason": "stopped"}
            name, args = decision["tool"]
            result = invoke_tool(name, args)
            trajectory.append(ToolCall(name, args, result))
            state += f"\n[{name} {args} -> {result}]"
        return {"answer": None, "trajectory": trajectory,
                "reason": "max_iterations"}


class CostTracker:
    """给工具调用计次数、算成本（W6-D4）。"""
    def __init__(self, price=0.001):
        self.price = price
        self.cost = 0.0
        self.count = 0
        self.per_step = []  # [(tool, 耗时), ...]

    def record(self, tool, elapsed):
        self.count += 1
        self.cost += self.price * elapsed
        self.per_step.append((tool, round(elapsed, 4)))


class Timer:
    """测一段代码跑多久：with Timer() as t: ... 然后 t.elapsed。"""
    def __init__(self):
        self.elapsed = 0.0

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.elapsed = time.time() - self.start


class TrackingAgent:
    """带成本追踪的 Agent：run 一次，统计全部开销（agent 当黑盒）。"""
    def __init__(self, planner, tracker=None, max_iterations=10):
        self.planner = planner
        self.tracker = tracker or CostTracker()
        self.max_iterations = max_iterations

    def run(self, prompt):
        tracker = self.tracker or CostTracker()
        answer, reason = None, "max_iterations"
        with Timer() as total:
            trajectory, state = [], ""
            for _ in range(self.max_iterations):
                decision = self.planner(trajectory, state)
                if "answer" in decision:
                    answer = decision["answer"]
                    reason = "stopped"
                    break
                name, args = decision["tool"]
                result = invoke_tool(name, args)
                trajectory.append(ToolCall(name, args, result))
                state += f"\n[{name} {args} -> {result}]"
        tracker.count += len(trajectory)
        tracker.per_step.append(("_total", round(total.elapsed, 4)))
        return {"answer": answer, "trajectory": trajectory,
                "reason": reason, "tracker": tracker}
