# auto-eval — 确定性自动化评测流水线（W7 工程化产出）

把 **W6 的四维度 Agent 评测框架**封装成一条**一键运行**的流水线：
`pytest 全量测试`（CI 门禁）+ `四维度打分报告`（可打印 / 可写文件 / 可 Docker）。

> 设计原则：**离线、确定性、可复现**。所有评测指标为确定性规则，**不依赖真实 LLM**，
> 不联网即可跑出分数。这正是 AI 测试岗位要的"可复现评测"工程能力。

---

## 目录结构

```
auto-eval/
├── README.md                # 本文件：安装 / 运行 / CI
├── requirements.txt         # 运行时依赖：pytest
├── Dockerfile               # 离线 wheels 安装镜像（容器内无网络也能装）
├── docker-compose.yml       # 一键跑通：docker compose run --rm auto-eval
├── run_evaluation.py        # CLI 一键入口：跑四维度评测 + 写报告
├── evaluate.py              # 评测引擎：被测 agent + 场景 → 四维度打分
├── system/                  # 被测系统（复用 W4 确定性 ReAct 骨架）
│   ├── agent.py             # ReActAgent / DeterministicPlanner / MemoryAgent
│   └── tools.py             # 工具集（add / multiply / lookup）
├── metrics/                 # 四维度指标封装
│   └── __init__.py          # Tool / Memory / Cost-Latency / DeepEval
├── reports/                 # 报告输出目录（evaluation_YYYYmmdd_HHMMSS.json/.txt）
└── tests/                   # pytest 全量用例（11 用例，覆盖四维度）
    ├── test_tool_calling.py
    ├── test_memory_and_cost.py
    └── test_deepeval.py
```

---

## 四维度评测

| 维度 | 指标 | 测什么 |
|---|---|---|
| 工具调用 | `ToolCallingMetric` | 工具名 / 参数值 / 参数名 / 调用顺序 / 次数全部正确 |
| 记忆 | `MemoryMetric` | 记住的信息跨轮能被读取（记忆跨轮存活） |
| 成本 & 延迟 | `CostLatencyMetric` | 成本、延迟都在预算内 |
| DeepEval | `DeepEvalMetric` | 关键词命中 / 精确匹配（离线兜底，无需 key） |

---

## 快速开始

### 方式一：本地直接跑（需要 Python 3.10+）

```bash
pip install -r requirements.txt

# 1) 跑全量测试（CI 门禁）
pytest tests/ -q
# 期望：11 passed

# 2) 一键评测（打印报告 + 写 reports/）
python run_evaluation.py
# 期望：总分 1.000，4/4 维度通过

# 2b) 额外打印 JSON 报告
python run_evaluation.py --json
```

### 方式二：Docker 一键跑通（推荐，离线、干净）

```bash
# 一次构建（镜像内离线安装 wheels，不联网）
docker build -t auto-eval:test .

# 跑全量测试（CI 门禁）
docker run --rm auto-eval:test

# 或走 compose 一键跑通（报告落到宿主机 reports/）
docker compose run --rm auto-eval
```

---

## CI 集成

`.github/workflows/pytest.yml` 在每次 push 时：拉代码 → 装 pytest → 跑 `pytest tests/ -q` →
11 用例全绿才通过（门禁）。本地用 Docker 镜像复现同一套流程。

---

## 设计要点（踩坑留痕）

1. **有状态规划器要新实例**：`DeterministicPlanner` 序列耗尽即结束，
   复用同一 agent 第二次 `run()` 会拿到空答案（`answer=None`），
   取 answer 必须另建一个 agent。已修。
2. **离线 wheels 安装**：容器内默认无网络，`pip install` 必须 `--no-index --find-links`
   从预好的 wheels 取，否则 `Temporary failure in name resolution` 报错。
3. **确定性兜底**：DeepEval 默认走确定性规则，不加载 LLM、不触发联网鉴权。

---

## 验收清单

- [x] 11 个 pytest 用例全绿
- [x] `python run_evaluation.py` 跑通四维度评测，总分 1.000
- [x] Docker 镜像离线构建成功，`docker run` / `docker compose run` 一键跑通
- [x] GitHub Actions CI 接入，push 即跑全量测试
- [x] 报告可写 JSON + TXT 到 reports/
