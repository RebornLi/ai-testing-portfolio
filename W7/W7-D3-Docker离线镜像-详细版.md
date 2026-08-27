# W7-D3 详细学习内容 · Docker 离线镜像 + 离线 wheels 安装（6-8 小时版）

> 日期：2026-08-29（周六）｜ 主题：把评测做成**离线可复现**的 Docker 镜像
> 目标：`docker build` 不联网也能装依赖（离线 wheels），`docker run` 跑全量测试
> 验收：`auto-eval:test` 镜像，`docker run --rm auto-eval:test pytest tests/ -q` → 11 passed

---

## ⏰ 今日时间块（6-8 小时）

| 时间段 | 时长 | 内容 |
|---|---|---|
| 09:00-10:30 | 1.5h | Docker 分层缓存、为什么容器内默认无网络 |
| 10:30-12:00 | 1.5h | 离线 wheels：为什么 `pip install` 在无网容器会失败 |
| 14:00-16:00 | 2h | 实战：写 Dockerfile + requirements.txt + .dockerignore |
| 16:00-17:30 | 1.5h | 实战：`docker build` + `docker run` 离线跑通 |
| 19:00-20:30 | 1.5h | 概念笔记③ 落盘（Docker 镜像 + 离线依赖） |
| 20:30-21:00 | 0.5h | 学习日志 + commit |

---

## 一、为什么容器内默认无网络（1.5h）★ 今日重点

> 一句话：**Docker 镜像要"拿到哪都能跑"，就不能假设它有网、能装包。**

### 真实踩到的报错

```
WARNING: Retrying ... after connection broken by
'NewConnectionError(... Failed to establish a new connection:
[Errno -3] Temporary failure in name resolution)': /simple/pytest/
```

> `name resolution` 失败 = DNS 解析失败 = 容器内根本连不上 PyPI。
> 所以 `RUN pip install -r requirements.txt` 在容器里会**直接崩**。

---

## 二、离线 wheels 方案（1.5h）★ 核心

> 思路：**先在宿主机把 wheel 拉好，COPY 进镜像，容器内 `--no-index` 从本地取。**

### 主机预拉（一次性）

```bash
# 在宿主机上先把 pytest 依赖 wheel 拉到本地
pip download -d wheels/ pytest
```

### Dockerfile（关键：`--no-index --find-links`）

```dockerfile
# W7 自动化评测流水线 — 离线确定性评测镜像
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 把预拉好的 wheel 一并打进镜像
COPY wheels/ /app/wheels/

# 离线安装依赖（--no-index 禁止联网，只从本地 wheels 取）
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/app/wheels -r requirements.txt

# 复制评测代码
COPY . .

# 默认：跑全量测试（CI 门禁）
CMD ["pytest", "tests/", "-q"]
```

### .dockerignore（别把构建垃圾打进镜像）

```
__pycache__/
*.pyc
.pytest_cache/
reports/*.json
reports/*.txt
```

---

## 三、requirements.txt（2h）★ 产出①

```
# 离线确定性评测运行时依赖
# - pytest：跑全量测试 + 一键入口的 CI 门禁
# - deepeval：仅在启用"真实 LLM 断言"时才需要
#            （默认走确定性兜底，不加载）
pytest>=8.0
```

> 关键决策：**确定性评测不需要 deepeval**，默认只装 pytest，镜像更小、更快。

---

## 四、实测：docker build + run（2h）★ 产物全绿★

> 下面是这次**实跑的真实输出**（证据先行）。

```bash
docker build -t auto-eval:test .
docker run --rm auto-eval:test pytest tests/ -q
```

### 真实输出

```
#8 [3/6] COPY wheels/ /app/wheels/
#8 DONE
#9 [5/6] RUN pip install --no-cache-dir --no-index --find-links=/app/wheels -r requirements.txt
#9 1.569 Successfully installed ... pytest-9.1.1
#9 DONE 1.7s
#10 [6/6] COPY . .
#10 DONE 0.1s

=== 容器内跑全量测试 ===
...........                                                              [100%]
11 passed in 0.06s
```

> 三句话总结：
> 1. `pip install` **1.7s 跑完**（离线 wheels，不联网）。
> 2. `COPY . .` 把评测代码打进镜像。
> 3. 容器内 `pytest tests/ -q` → **11 passed**，离线、干净、可复现。

---

## 五、概念笔记③ 落盘（1.5h）★ 产出

> 一句话记忆点：
> 1. **容器内默认无网**：`pip install` 会 DNS 失败，别假设能联网。
> 2. **离线 wheels**：宿主机预拉 wheel → `COPY` 进镜像 → `--no-index --find-links` 本地装。
> 3. **分层缓存**：先 `COPY wheels` + `pip install`，再 `COPY . .`，代码改了不重装依赖。
> 4. **.dockerignore**：排除 `__pycache__/`、报告产物，镜像更干净。

---

## 六、验收清单

- [x] Dockerfile 离线 wheels 安装跑通（1.7s 装完）
- [x] 容器内 `pytest` → 11 passed
- [x] `.dockerignore` 排除构建垃圾
- [ ] 概念笔记③ 落盘
- [ ] 学习日志写了（含卡点）
- [ ] 已 commit

## ⏰ 卡点提示

- 漏了 `pygments`（pytest 的依赖）会 `No matching distribution`，先 `pip download pytest` 看全依赖。
- `.dockerignore` 里写 `reports/` 会把 `report.py` 源码一起删——要写 `reports/*.json` 只排除产物。

## 📝 学习日志

> 今天（08-29 周六）：
> 1. 学 Docker：容器内默认无网，pip install 会 DNS 失败。
> 2. 离线 wheels 方案：主机预拉 wheel → COPY 进镜像 → --no-index 本地装。
> 3. 漏了 pygments（pytest 依赖），补全 4 个 wheel 后装通（1.7s）。
> 4. 实测：docker build 成功，docker run 跑全量测试 11 passed。
> 5. 明天 D4 上 compose，一键跑通 + 报告落到宿主。

---
*创建于 W7-D3 · 计划：AI 求职阶段二 W7 第 7 周*
