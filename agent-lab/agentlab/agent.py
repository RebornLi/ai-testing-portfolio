"""agent.py — ReAct Agent 核心（确定性，可测试）。

ReAct = Reasoning + Acting。每一轮：
    1. 看当前轨迹（之前做了什么）
    2. 规划器决定下一步动作（tool_call 或最终答案）
    3. 执行工具（若有）→ 观察结果
    4. 重复直到终止（最终答案 或 超过 max_iterations）

设计重点 —— “规划器”是注入的：
    - 生产环境规划器 = LLM 的规划能力（思考该调哪个工具）
    - 测试环境规划器 = 确定性函数（固定动作序列，可复现）
    这样测试不依赖真实模型，只测“轨迹 + 终止 + 工具正确性”。

认知边界：真实 Agent 的规划器输出 JSON（name/args）；
这里用一个轻量规划接口，测试用确定性规划器替换。
"""
from agentlab.tools import TOOLS, invoke_tool


class MemoryFull(Exception):
    """记忆满（超出容量）时抛出。"""
    pass


class Memory:
    """简单键值记忆 + 容量上限（测试用）。

    认知边界：真实 Agent 的记忆 = 长期上下文 / 外部存储，容量无限。
    这里用一个固定容量的字典模拟，测“写/检索/遗忘/容量上限”行为。
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

    def __contains__(self, key):
        return key in self.data

    def __len__(self):
        return len(self.data)


class ToolCall:
    """一个工具调用步骤。"""

    def __init__(self, name, args, result=None):
        self.name = name
        self.args = args
        self.result = result

    def __repr__(self):
        return f"<ToolCall {self.name} {self.args} -> {self.result}>"


class ReActAgent:
    """ReAct Agent：按规划器动作序列执行，记录轨迹，强制终止。

    planner: callable(history, state) -> {"tool": (name, args)}
             或 {"answer": text}
             history: 已执行的工具调用列表
             state: 累积的观察结果字符串
    """

    def __init__(self, planner, max_iterations=10):
        self.planner = planner
        self.max_iterations = max_iterations

    def run(self, initial_prompt):
        """执行任务，返回 {"answer", "trajectory", "reason": text}。

        终止条件：
          - 规划器给出 answer → 正常结束（reason="stopped"）
          - 序列用尽仍未 answer → 正常结束（reason="sequence_end"，无答案）
          - 超过 max_iterations → 强终止（reason="max_iterations"）
        """
        trajectory = []
        state = ""

        for _ in range(self.max_iterations):
            try:
                decision = self.planner(trajectory, state)
            except StopIteration:
                return {
                    "answer": None,
                    "trajectory": trajectory,
                    "reason": "sequence_end",
                }

            if "answer" in decision:
                return {
                    "answer": decision["answer"],
                    "trajectory": trajectory,
                    "reason": "stopped",
                }

            name, args = decision["tool"]
            result = invoke_tool(name, args)
            call = ToolCall(name, args, result)
            trajectory.append(call)
            state = state + f"\n[{name} {args} -> {result}]"

        return {
            "answer": None,
            "trajectory": trajectory,
            "reason": "max_iterations",
        }

    def replay(self, trajectory):
        """重放一段轨迹，返回每步的工具结果列表 [result, ...]。

        重放 = 只重新执行轨迹里的 tool_call，不复跑规划器。
        这是 Agent 测试的关键能力：轨迹自包含、可复现。
        """
        results = []
        for call in trajectory:
            results.append(invoke_tool(call.name, call.args))
        return results


class DeterministicPlanner:
    """确定性规划器：给定固定动作序列，逐步执行。

    用法：传入一个动作列表，如
        steps = [("tool", "add", {"a": 3, "b": 4}),
                 ("answer", "7")]
    规划器依次返回这些动作。

    认知边界：这是测试用的固定策略。真实 Agent 的规划由 LLM 决定，
    这里用确定序列模拟一个“已知的正确答案路径”。
    """

    def __init__(self, steps):
        self.steps = list(steps)
        self.index = 0

    def __call__(self, history, state):
        if self.index >= len(self.steps):
            # 序列用完了，通知调用方终止（run() 会捕获 StopIteration）
            raise StopIteration
        kind, *rest = self.steps[self.index]
        self.index += 1
        if kind == "tool":
            name, args = rest
            return {"tool": (name, args)}
        return {"answer": rest[0]}


class LoopingPlanner:
    """失控规划器：永远只返回 tool_call，从不给出 answer。

    用于测“终止性”：Agent 必须在 max_iterations 后强终止。
    这里固定重复同一个 tool，轨迹会无限增长。
    """

    def __init__(self, name="add", args=None):
        self.name = name
        self.args = args or {"a": 1, "b": 1}

    def __call__(self, history, state):
        return {"tool": (self.name, self.args)}
