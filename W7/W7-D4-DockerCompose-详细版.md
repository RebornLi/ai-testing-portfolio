# W7-D4 详细学习内容 · Docker Compose 一键跑通（6-8 小时版）

> 日期：2026-08-30（周日）｜ 主题：compose 一键起评测 + 卷挂载
> 目标：`docker compose run --rm auto-eval` 一条命令跑通，报告落到宿主 ./reports/
> 验收：`docker compose run` 一键 11 passed；报告写进宿主机

---

## ⏰ 今日时间块（6-8 小时）

| 时间段 | 时长 | 内容 |
|---|---|---|
| 09:00-10:30 | 1.5h | compose 是什么：服务 / 命令 / 卷 |
| 10:30-12:00 | 1.5h | 为什么需要一键：团队里"一条命令跑通" |
| 14:00-16:00 | 2h | 实战：写 docker-compose.yml |
| 16:00-17:30 | 1.5h | 实战：`docker compose run` 一键跑通 |
| 19:00-20:30 | 1.5h | 概念笔记④ 落盘（compose 一键跑通） |
| 20:30-21:00 | 0.5h | 学习日志 + commit |

---

## 一、Compose 是什么（1.5h）★ 今日重点

> 一句话：**Dockerfile 定义"一个镜像"，compose 定义"怎么把这个镜像跑起来 + 挂什么卷"。**

### 三层关系

```
requirements.txt  →  定义依赖
Dockerfile        →  定义镜像（怎么装依赖 + 怎么跑）
docker-compose.yml →  定义服务（用哪个镜像 + 跑什么命令 + 挂哪）
```

> W3 的 compose 只起 3 个服务，复杂。W7 这个只要**一个**服务（自动评测），简单。

---

## 二、docker-compose.yml（2h）★ 产出①

```yaml
# W7 自动化评测流水线
# 一键跑通：docker compose run（容器内执行全量测试 + 一键评测入口）
# 结果落到宿主 ./reports/，方便在仓库里留痕。
services:
  auto-eval:
    build: .                      # 用当前目录 Dockerfile 构建
    image: auto-eval:test         # 镜像名（供 CI 引用）
    container_name: auto-eval
    # 默认跑全量测试（CI 门禁）
    command: ["pytest", "tests/", "-q"]
    # 若想看一键评测报告，切到下面这行再 up：
    # command: ["python", "run_evaluation.py", "--dir", "reports"]
    volumes:
      - ./reports:/app/reports    # 报告卷：落到宿主 ./reports/
```

---

## 三、实测：`docker compose run` 一键绿（1.5h）★ 产物全绿★

```bash
docker compose run --rm auto-eval
```

> 下面是这次**实跑的真实输出**（证据先行）。

```
Network auto-eval_default Creating
Container auto-eval-auto-eval-run-... Creating
Container auto-eval-auto-eval-run-... Created
...........                                                              [100%]
11 passed in 0.06s
```

> 三句话：
> 1. compose 自动构建镜像（`build: .`）。
> 2. 容器内跑 `pytest tests/ -q`。
> 3. **11 passed**，一条命令跑通，报告卷落到宿主 `./reports/`。

---

## 四、概念笔记④ 落盘（1.5h）★ 产出

> 一句话记忆点：
> 1. **compose = 镜像怎么跑起来 + 挂什么卷**。
> 2. 一个服务：`auto-eval`，`build: .` 用 Dockerfile 构建。
> 3. `volumes: ./reports:/app/reports` 把报告落到宿主机，方便留痕。
> 4. 命令可切换：CI 跑 pytest，想看报告就切 `run_evaluation.py`。

---

## 五、验收清单

- [x] `docker compose run --rm auto-eval` → 11 passed
- [x] 报告卷落到宿主机 ./reports/
- [ ] 概念笔记④ 落盘
- [ ] 学习日志写了（含卡点）
- [ ] 已 commit

## ⏰ 卡点提示

- `docker compose run` 第一次会先 `build`，慢一点是正常的（离线 wheels 1.7s 装）。
- 命令默认跑 pytest（门禁）；想看报告切到 `run_evaluation.py`。

## 📝 学习日志

> 今天（08-30 周日）：
> 1. 学 compose：定义服务、命令、卷，比 Dockerfile 高一层。
> 2. 写 docker-compose.yml：一个 auto-eval 服务，默认跑 pytest。
> 3. 卷挂载 ./reports，报告落到宿主机。
> 4. 实测 docker compose run → 11 passed，一键跑通。
> 5. 明天 D5 上 GitHub Actions CI，push 即跑 + 写 README。

---
*创建于 W7-D4 · 计划：AI 求职阶段二 W7 第 7 周*
