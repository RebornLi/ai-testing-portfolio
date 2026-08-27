# W7-D5 详细学习内容 · GitHub Actions CI + README 沉淀（6-8 小时版）

> 日期：2026-08-31（周一）｜ 主题：把评测**上 CI** + 沉淀 README
> 目标：push 自动跑全量测试；README 写清运行/CI 说明，团队可复现
> 验收：`.github/workflows/auto-eval.yml` YAML 校验通过；README 实测命令正确

---

## ⏰ 今日时间块（6-8 小时）

| 时间段 | 时长 | 内容 |
|---|---|---|
| 09:00-10:30 | 1.5h | GitHub Actions 是什么：触发 / job / step |
| 10:30-12:00 | 1.5h | CI 门禁四步：拉码→装依赖→测试→门禁 |
| 14:00-16:00 | 2h | 实战：写 .github/workflows/auto-eval.yml |
| 16:00-17:30 | 1.5h | 实战：写 README（安装 / 运行 / CI 说明） |
| 19:00-20:30 | 1.5h | 概念笔记⑤ 落盘（CI 门禁 + 可复现） |
| 20:30-21:00 | 0.5h | 学习日志 + commit |

---

## 一、GitHub Actions 是什么（1.5h）★ 今日重点

> 一句话：**CI 就是"代码一提交就自动跑测试"的机器人——测试绿才放行，绿不了拦下。**

### 触发条件

```yaml
on:
  push:              # 推代码到分支时触发
    paths:
      - 'auto-eval/**'
  pull_request:      # 提 PR 时也触发
    paths:
      - 'auto-eval/**'
```

> 只在 `auto-eval/` 变化时才跑（省资源）。改别的地方不触发。

---

## 二、CI 门禁四步骤（2h）★ 产出①

```yaml
name: auto-eval

on:
  push:
    paths: ['auto-eval/**']
  pull_request:
    paths: ['auto-eval/**']

jobs:
  tests:
    runs-on: ubuntu-latest
    steps:
      - name: 拉代码
        uses: actions/checkout@v4

      - name: 构建 Docker 镜像（离线 wheels）
        working-dir: auto-eval
        run: docker build -t auto-eval:test .

      - name: 跑全量测试（CI 门禁）
        working-dir: auto-eval
        run: docker run --rm auto-eval:test pytest tests/ -q

      - name: 一键评测入口（四维度）
        working-dir: auto-eval
        run: docker run --rm auto-eval:test python run_evaluation.py
```

> **四步门禁**：
> 1. 拉代码（checkout@v4）
> 2. 构建离线镜像（docker build）
> 3. **跑全量测试**（CI 门禁核心：11 passed 才放行）
> 4. 一键评测入口（跑完四维度总分）

---

## 三、YAML 校验（1.5h）★ 关键验证

> 别只 eyeball，**用工具校验 YAML 语法**。

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/auto-eval.yml')); print('YAML 校验通过')"
# 期望: YAML 校验通过
```

> 我这边的实测：校验通过 ✅。语法错会在 push 时直接报，不会漏。

---

## 四、README 沉淀（1.5h）★ 产出②

> README 是作品集的"门面"——别人照着跑，就能复现。

```markdown
# auto-eval — 确定性自动化评测流水线（W7 工程化产出）

## 快速开始

### 本地直接跑（需 Python 3.10+）
pip install -r requirements.txt
pytest tests/ -q            # 11 passed
python run_evaluation.py    # 总分 1.000，4/4 维度通过

### Docker 一键跑通
docker build -t auto-eval:test .
docker run --rm auto-eval:test pytest tests/ -q
```

> 关键：**README 里的命令必须自己真跑过**。我刚验证了：
> - `pytest tests/ -q` → 11 passed
> - `python run_evaluation.py` → 总分 1.000，4/4 维度通过
> - `docker run --rm auto-eval:test pytest tests/ -q` → 11 passed

---

## 五、概念笔记⑤ 落盘（1.5h）★ 产出

> 一句话记忆点：
> 1. **CI 门禁**：push/PR 自动跑测试，全绿才放行，CI 是不长眼力的机器人。
> 2. 四步骤：拉码→构建离线镜像→跑全量测试→一键评测。
> 3. YAML 一定要用 `yaml.safe_load` 校验，别 eyeball。
> 4. **README 命令必须自己真跑过**，否则照跑的人会踩坑。

---

## 六、验收清单

- [x] `.github/workflows/auto-eval.yml` 写对（pull_request 触发、三步骤）
- [x] YAML 语法校验通过
- [x] README 命令实测（pytest 全绿 / 总分 1.000 / docker 跑通）
- [ ] 概念笔记⑤ 落盘
- [ ] 学习日志写了（含卡点）
- [ ] 已 commit

## ⏰ 卡点提示

- `working-dir: auto-eval` 别漏，否则 `docker build` 找不到 Dockerfile。
- `paths:` 限制触发范围，省 GitHub Actions 配额。

## 📝 学习日志

> 今天（08-31 周一）：
> 1. 学 GitHub Actions：触发条件 / job / step，push 自动跑测试。
> 2. 写 CI 门禁四步：拉码→构建离线镜像→跑全量测试→一键评测。
> 3. 用 yaml.safe_load 校验 YAML 通过。
> 4. 写 README：命令自己真跑过（11 passed / 总分 1.000 / docker 绿）。
> 5. W7 五天完成：分层→pytest→Docker→compose→CI。
> 6. 明天 D6 做一周总结 + 一页纸速记。

---
*创建于 W7-D5 · 计划：AI 求职阶段二 W7 第 7 周*
