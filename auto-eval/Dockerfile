# W7 自动化评测流水线 — 离线确定性评测镜像
# 不依赖真实 LLM：所有指标为确定性规则，保证 CI 可复现。
# 关键：容器内默认无网络，用宿主机预拉好的 wheels 离线安装（pip）。
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
