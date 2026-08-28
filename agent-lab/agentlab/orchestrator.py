"""orchestrator.py — 多智能体编排（确定性，可测试）。

多智能体编排 = 一个主控 Orchestrator 把子任务分发给多个子 Agent，
再汇总各子 Agent 的返回。这是 roadmap Phase 4 的差异化维度：
"mock 子 Agent 返回，断言分发/汇总逻辑"。

设计重点：
- MockSubAgent：确定性子 Agent 替身，.run(query) 返回注入函数结果。
  真实子 Agent 是 LLM，这里用固定函数替身，只测编排逻辑。
- Orchestrator：按 routing 分发子任务，按 queries 汇总子 Agent 结果。
- SequentialOrchestrator：按 sequence 顺序跑子 Agent，遇未知 Agent
  记 reason="unknown_agent" 但跳过继续（轨迹可复现）。

认知边界：真实多智能体 = 主控 Agent 动态决定分发给谁、几轮。
这里用确定序列模拟，测"编排结构"而非动态规划。
"""


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
        """把 routed 的子任务交给对应子 Agent，返回 {task_name: result}。

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
        """顺序执行 sequence 里的子 Agent，返回 {output, reason}。

        遇未知子 Agent → 记 reason="unknown_agent" 并跳过继续。
        output = 各结果以 "+" 拼接（跳过未知项）。
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
