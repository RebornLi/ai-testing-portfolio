# eval-lab · Agent 自动化评测框架（W5-6 落地）

> 真实可跑的 Agent 评测框架：确定性 agent + 四维度打分 + 11 用例全绿。
> 对应 W6 笔记「给 Agent 打分」的四维度方法论（工具调用 / 任务完成率 / 上下文记忆 / 成本延迟 + DeepEval）。

## 运行

```bash
python -m pytest eval-lab/tests/ -q
```

## 产物

```
eval-lab/
├── README.md           # 本文件
├── conftest.py         # 环境：把 eval_lab 加入 sys.path
├── eval_lab/           # 被测 Agent + 度量
│   ├── tools.py        # 确定性工具集（add/multiply/lookup/weather）
│   ├── agent.py        # ReActAgent / MemoryAgent / TrackingAgent + 规划器
│   └── metrics.py      # 四维度打分函数 + DeepEval 确定性 metric
├── tests/              # pytest 全量用例（四维度）
│   ├── test_tool_calling.py         # D2 工具调用 6 个断言关注点
│   ├── test_context_completion.py   # D3 任务完成率 + 多轮上下文
│   ├── test_cost_latency.py         # D4 成本 & 延迟
│   └── test_deep_eval.py            # D5 DeepEval 自动化评测
└── reports/            # 报告输出（evaluation_*.json/.txt）
```

## 四维度

| 维度 | 测试 | 度量 |
|---|---|---|
| 工具调用 | `test_tool_calling.py` | `score_tool_calling` — 每步 name/参数/结果全对 |
| 任务完成率 | `test_context_completion.py` | `completion_rate` — 必要步骤走没走全 |
| 上下文记忆 | `test_context_completion.py` | `score_context_memory` — 多轮靠 memory 复用 |
| 成本延迟 | `test_cost_latency.py` | `score_cost_latency` / `quality_score` |
| DeepEval | `test_deep_eval.py` | `KeywordMetric` + `run_deep_eval`（不依赖 key） |

## 验收

- pytest 全绿（`pytest eval-lab/tests/ -q` → 通过）
- 坏 Agent 的错误能被断言抓住（先失败后实现）
- 确定性、离线、可复现

---

*创建于 W6 · AI 求职作品集*
