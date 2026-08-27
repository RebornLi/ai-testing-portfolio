# security-lab — Prompt Injection 安全测试流水线（W8 工程化产出）

把 **W7 的自动化评测框架**从"功能正确性"延伸到"**安全性**"：
`pytest 全量安全测试`（CI 门禁）+ `三维度安全审计`（可打印 / 可写文件 / 可 Docker）。

> 设计原则：**离线、确定性、可复现**。所有审计维度为确定性规则，**不依赖真实模型**，
> 不联网即可跑出分数。攻击语料是预置的，被测 agent 是确定性替身，
> 证明审计流水线能**区分**漏洞 agent 和安全 agent。

---

## 目录结构

```
security-lab/
├── README.md                # 本文件：安装 / 运行 / CI
├── requirements.txt         # 运行时依赖：pytest
├── Dockerfile               # 离线 wheels 安装镜像（容器内无网络也能装）
├── .dockerignore
├── run_evaluation.py        # CLI 一键入口：跑三维度安全审计 + 写报告
├── evaluate.py              # 安全审计引擎：agent + 攻击语料 → 三维度打分
├── security/                # 三个安全维度指标
│   └── __init__.py          # score_injection_guarding / permission / output_masking
├── system/                  # 被测系统
│   └── vault.py             # InsecureAgent(漏洞) / SecureAgent(修复) + 权限保险库
├── reports/                 # 报告输出目录（evaluation_YYYYmmdd_HHMMSS.json/.txt）
└── tests/                   # pytest 全量用例（10 用例，覆盖三维度 + 对比打分）
    └── test_security.py
```

---

## 三个安全维度

| 维度 | 指标 | 测什么 |
|---|---|---|
| prompt injection 防护 | `score_injection_guarding` | 攻击指令是否被照做（injected 标志） |
| 权限边界 | `score_permission_boundary` | 越权是否拿到机密（双路断言：越权要拒、合法放行） |
| 敏感信息泄露 | `score_output_masking` | 攻击是否让 agent 输出明文机密 |

审计默认跑两个 agent 做**正负对照**：
- **InsecureAgent**（默认实现，含 3 处漏洞）→ 审计必须抓住它，判 FAIL（0.000）
- **SecureAgent**（修复版）→ 三维度全通过，判 PASS（1.000）

---

## 快速开始

### 本地直接跑（需要 Python 3.10+）

```bash
pip install -r requirements.txt

# 1) 跑全量安全测试（CI 门禁）
pytest tests/ -q
# 期望：10 passed

# 2) 一键安全审计（打印报告 + 写 reports/）
python run_evaluation.py
# 期望：InsecureAgent FAIL 0.000、SecureAgent PASS 1.000
```

### 方式二：Docker 一键跑通（推荐，离线、干净）

```bash
# 一次构建（镜像内离线安装 wheels，不联网）
docker build -t security-lab:test .

# 跑全量安全测试（CI 门禁）
docker run --rm security-lab:test pytest tests/ -q

# 或跑一键安全审计
docker run --rm security-lab:test python run_evaluation.py
```

---

## CI 集成

`.github/workflows/security-lab.yml` 在每次 push 时：拉代码 → 构建离线镜像 → 跑 `pytest tests/ -q`（全绿才是门禁）→ 跑安全审计。

---

## 设计要点（踩坑留痕）

1. **安全审计 = 正负对照**：只测安全 agent 会自我感觉良好。必须同时跑有漏洞的 agent，
   审计才有"能抓住真问题"的可信度。
2. **维度指标走 agent.process()**：安全测试测的是 agent 行为，不是直接测保险库。
   三个维度统一通过 `agent.process(prompt)` 验证，返回 `(score, passed, errors)` 三元组。
3. **双路权限断言**：权限测试要同时断言"越权被拒"和"合法放行"，否则会漏判。

---

## 验收清单

- [x] 10 个 pytest 用例全绿
- [x] `python run_evaluation.py` 跑通三维度审计（对比打分）
- [x] Docker 镜像离线构建成功，`docker run` 跑全量测试 + 审计
- [x] GitHub Actions CI 接入，push 即跑全量安全测试
- [x] README 可复现（实测命令正确）

---
*创建于 W8 · 计划：AI 求职阶段二 W8 第 8 周*
