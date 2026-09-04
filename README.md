# AI 测试工程师 · 8 周学习笔记 + 作品集

> **状态**：📅 2026-08 启动 ｜ 8 周学习路线 · 每日学习打卡 · 每周可演示成果
> **铁律**：代码块必须实跑绿（NO COMPLETION CLAIMS WITHOUT VERIFICATION）
> **身份**：`github.com/RebornLi`

---

## 🎯 学习目标

转型 **AI 应用 / Agent 评测工程师**（软件测试 → AI 测试）：为 LLM 应用、RAG 系统、AI Agent 做**全链路质量保障**——从"会造 Agent"到"会评测 Agent"，再到"会安全地评测 Agent"。

整条路线分三步：**工具底座（pytest）→ 应用评测（RAG/Agent/LLM）→ 工程化与安全（CI / Docker / 安全审计）**。

---

## 🗺️ 8 周路线

| 周 | 主题 | 落产物 | 验收（实测全绿） |
|---|---|---|---|
| **W1** | Python 工程化 + pytest + 接口测试 | `jd-validator` 随堂项目（笔记） | 参数化 14+ 用例全绿 |
| **W2** | LLM API 调用测试（参数化/流式/FunctionCalling） | LLM 压测套件（笔记） | 多参数批量调用 + 响应校验 |
| **W3** | RAG 评测（向量检索 / 幻觉 / 答案打分） | `rag-demo/` | 53 用例全绿 |
| **W4** | Agent 测试（ReAct / 工具链 / 多智能体） | `agent-lab/` | 65 用例全绿 |
| **W5** | ML/DL 扫盲（神经网络 → embedding → Transformer） | 概念笔记 + numpy 实战 | 5 概念速记 + 自测 |
| **W6** | Agent 四维度评测 + DeepEval | `eval-lab/` | 22 用例全绿 |
| **W7** | 自动化评测流水线（离线 Docker + CI） | `auto-eval/` | 11 用例全绿 + Docker + CI |
| **W8** | 安全测试审计（注入 / 越权 / 泄露） | `security-lab/` | 10 用例全绿 + Docker + CI |

> W1–W2 以学习笔记 + 随堂练习为主（尚未沉淀为独立工程）；W3–W8 均有**可运行的独立工程** + pytest 全量用例。

---

## 🗂️ 可运行工程导航

每个 lab 都是「被测系统 + 指标 + 评测引擎 + pytest 全量 +（离线 Docker + CI）」的完整结构：

- `rag-demo/` — 自建 RAG 系统（向量检索 / 质量 / 报告）+ 检索质量评测 —— **W3**
- `agent-lab/` — ReAct Agent：工具调用 / 记忆 / 多智能体编排 + 确定性测试 —— **W4**
- `eval-lab/` — Agent 四维度评测框架（工具调用 / 任务上下文 / 成本延迟 / DeepEval）—— **W5–W6**
- `auto-eval/` — 自动化评测流水线，离线 wheels + Docker 一键评测 —— **W7**
- `security-lab/` — Prompt Injection / 越权 / 泄露 三类攻击审计（漏洞版 vs 安全版对照）—— **W8**

## ▶️ 快速开始

```bash
# 根目录直接跑全量（pytest.ini 用 --import-mode=importlib 解决跨 lab 文件名冲突）
python -m pytest rag-demo -q          # 53 passed
python -m pytest agent-lab -q         # 65 passed
python -m pytest eval-lab -q          # 22 passed
python -m pytest auto-eval -q         # 11 passed
python -m pytest security-lab -q      # 10 passed
```

**离线 / CI**（每个 lab 自带）：

```bash
cd security-lab
docker build -t security-lab:test .      # 离线 wheels 安装，容器内无网也能跑
docker run --rm security-lab:test pytest tests/ -q
docker run --rm security-lab:test python run_evaluation.py   # 一键三维度审计
```

## 🚀 CI

GitHub Actions 在 push 改动时触发，跑对应 lab 的全量测试作门禁：

- `.github/workflows/auto-eval.yml`
- `.github/workflows/security-lab.yml`

---

## 📓 学习路线笔记（W1–W8）

每个 `Wx/` 文件夹是该周的完整学习记录，**可直接阅读**：

- `Wx-详细学习计划.md`（**周目标 + 每日任务 + 产出物清单 + 验收清单**；W1–W8 齐全）
- `Wx-Dn-<主题>-详细版.md`（**每日详细笔记**：时间块 → 概念 → 可跑代码 → 卡点 → 学习日志 → 自检清单 → 关键词）
- `Wx-一周总结-详细版.md`（**本周主线 + 验收证据 + 踩坑 + 日志汇总 + 关联展望**，部分周有）

> 每日笔记里的「验收用例数」是**写作当天的数值**（例如 W4-D1 写 22，后来 `agent-lab` 持续扩到 65），属于学习日志的正常演进，按当天语境阅读即可。

**笔记总览**：

- [W1](W1/) — Python 工程化 + pytest + 接口测试
- [W2](W2/) — LLM API 调用测试
- [W3](W3/) — RAG 评测
- [W4](W4/) — Agent 测试
- [W5](W5/) — ML/DL 扫盲
- [W6](W6/) — Agent 四维度评测
- [W7](W7/) — 自动化评测流水线
- [W8](W8/) — 安全测试审计

---

## 📈 求职进度

- [ ] W2 末：投递首批 OD / 外包岗
- [ ] W6 末：投递 Agent 公司测试岗 + 开源 PR
- [ ] W8 起：主投目标岗（腾讯云智等），每日 10+ 沟通

## 📞 联系

- GitHub: [`RebornLi`](https://github.com/RebornLi)（邮箱待补充）

---

*本仓库为求职作品集 + 学习记录，所有工程均为独立完成。代码块均按「实跑绿」铁律编写，欢迎 Star / Issue 交流。*
