"""agent.py — ReAct Agent 核心（确定性，可测试）

复用 W4 确定性骨架。被测系统，供 auto-eval 流水线评测。

planner: callable(history, state) -> {"tool": (name, args)} 或 {"answer": text}
max_iterations: 硬上限，超过则强终止（防止死循环）。
"""
from tools import invoke_tool


class ToolCall:
    """一个工具调用步骤。"""
    def __init__(self, name, args, result=None):
        self.name, self.args, self.result = name, args, result


class ReActAgent:
    """ReAct Agent：按规划器动作序列执行，记录轨迹，强制终止。"""

    def __init__(self, planner, max_iterations=10):
        self.planner = planner
        self.max_iterations = max_iterations

    def run(self, initial_prompt):
        """执行任务，返回 {"answer", "trajectory", "reason"}。

        reason 三态：
          - "stopped"          规划器给出 answer，正常结束
          - "sequence_end"     确定性序列耗尽仍未 answer
          - "max_iterations"   失控循环，硬上限强终止
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

    def replay(self, trajectory):
        """重放轨迹，返回每步结果 [result, ...]（离线重跑，验证一致性）。"""
        return [invoke_tool(c.name, c.args) for c in trajectory]


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


class MemoryAgent:
    """带 Memory 的 Agent：多轮对话中记住关键信息（D3 多轮上下文被测）。"""
    def __init__(self, memory, planner, max_iterations=10):
        self.memory, self.planner, self.max_iterations = memory, planner, max_iterations

    def run(self, prompt):
        return self.planner(prompt, self.memory, self.max_iterations)


class Memory:
    """最小记忆：支持写-读-清空，跨轮存活于同一 agent 实例。"""
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
