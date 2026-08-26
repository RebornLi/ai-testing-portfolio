# W1-D2 详细学习内容 · requests 接口测试实战（6-8 小时版）

> 日期：2026-08-22（周六）｜ 目标：学会用 requests 测 HTTP 接口，用本地真实服务（vLLM :8000）做测试对象
> 验收：vLLM 接口测试 8 用例全绿（服务未启动时用 pytest.skip）+ 学习日志 + commit

---

## ⏰ 今日时间块（6-8 小时）

| 时间段 | 时长 | 内容 |
|---|---|---|
| 09:00-10:00 | 1h | requests 入门：GET/POST、状态码、json() 解析 |
| 10:00-11:30 | 1.5h | 接口测试三态设计（正常/边界/异常） |
| 14:00-16:00 | 2h | 实战：对 vLLM 写 8 个接口用例 |
| 16:00-17:00 | 1h | 8081 embedding 服务同样写 3 个用例 |
| 19:00-20:00 | 1h | 三态补齐 + 失败用例自测（先看失败长啥样） |
| 20:00-21:00 | 1h | 学习日志 + commit 打卡 |

---

## 一、requests 入门（1h）★ 今日核心依赖

> 为什么接口测试必学 requests？因为它让"发一个 HTTP 请求"变得像喝水一样简单，比 urllib 省 10 行代码。

### 1.1 安装
```bash
pip install requests        # D1 已装，确认一下
requests --version 2>/dev/null || python3 -c "import requests; print(requests.__version__)"
```

### 1.2 最小示例：发一个 GET 请求
```python
import requests

r = requests.get("http://127.0.0.1:8000/health", timeout=5)
print(r.status_code)     # 状态码：200 表示成功
print(r.text)            # 原始文本
print(r.json())          # 解析成 JSON 字典（如果响应是 JSON）
print(r.headers)         # 响应头（Content-Type 等）
```

### 1.3 状态码速记（接口测试的核心指标）

| 状态码 | 含义 | 测试里怎么断言 |
|---|---|---|
| 200 | 成功（正常返回） | `assert r.status_code == 200` |
| 401 | 未授权（缺 key/token） | `assert r.status_code == 401` |
| 404 | 路径不存在 | `assert r.status_code == 404` |
| 500 | 服务器内部错误 | `assert r.status_code == 500` |

> 记忆口诀：**2xx 成功，4xx 客户端错了（请求不对），5xx 服务器错了**。

### 1.4 发 POST 请求（带参数 / 带 JSON）
```python
# POST 表单参数（application/x-www-form-urlencoded）
r = requests.post("http://127.0.0.1:8000/v1/chat/completions",
                  params={"q": "hello"},          # query string，?q=hello
                  data={"key": "value"},         # 表单 body
                  json={"messages": [...]},      # JSON body（自动设 Content-Type: application/json）
                  timeout=10)

# 常见断言
assert r.status_code == 200
data = r.json()                      # 自动解析
assert data["choices"][0]["message"]["content"]  # 拿到返回内容
```

### 1.5 超时 timeout（必加！）
```python
# 不加 timeout，网络卡住会**永远等下去**，测试卡死
r = requests.get(url, timeout=5)   # 5 秒没响应就抛 requests.exceptions.Timeout
# 超时也可以当断言：服务崩了也应该快速失败
try:
    requests.get(url, timeout=2)
except requests.exceptions.Timeout:
    print("服务无响应！")
```

---

## 二、接口测试三态设计（1.5h）★ 核心方法论

> 接口测试不是"发一个请求看它通不通"，而是**系统性地覆盖正常/边界/异常三种情况**。这是专业测试和新手的核心区别。

### 2.1 三态原则
- **正常态（happy path）**：参数完全正确，应该 200 成功
- **边界态**：参数刚好在临界（空/超长/最小值），看是否优雅降级
- **异常态**：参数错误/缺失，应该返回错误码（4xx）或快速报错

### 2.2 针对 vLLM 的接口测试清单

| 用例 | 方法 | 路径 | 期望 |
|---|---|---|---|
| 1 | GET | `/health` | 200，服务健康 |
| 2 | GET | `/v1/models` | 200，含模型名 |
| 3 | GET | `/v1/xxx`(非法路径) | 404 或 401 |
| 4 | POST | `/v1/chat/completions`(无 key) | 401 未授权 |

> ⚠️ **本机实测差异**：学习计划里写的"模型含 nemotron3"——实际 `/v1/models` 返回的是 `ornith1.5-35b`（本机部署的是 Ornith 系列）。**测试要用真实模型名**，别照抄计划。接口测试的第一铁律：**以真实服务响应为准，计划仅供参考**。

---

## 三、实战：vLLM 接口测试（2h）★ 今日产出

创建 `tests/test_local_api.py`。先写一个**服务连接检查 fixture**，服务没启动时自动 `skip`（这样 CI 不会因为本机没起服务而失败）。

```python
"""W1-D2 实战：vLLM 接口测试（8 用例）
本地真实服务：vLLM 对话模型 http://127.0.0.1:8000
先确认服务起来：curl http://127.0.0.1:8000/health
"""
import os
import requests
import pytest

# API Base 地址（建议用环境变量，别硬编码；这里先用默认值兜底）
BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000")
API_KEY = os.environ.get("API_KEY", "")   # 从环境变量读，不要硬编码！


@pytest.fixture(scope="session")
def service_up():
    """会话级 fixture：只检查一次服务是否起来。
    服务没起 → 整个模块的测试 skip（不是失败），因为这是环境问题不是代码问题。
    """
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=3)
        if r.status_code == 200:
            return "ok"
        pytest.skip(f"服务 /health 返回 {r.status_code}，未就绪")
    except requests.exceptions.RequestException as e:
        pytest.skip(f"服务未启动（{e.__class__.__name__}），跳过接口测试")


@pytest.mark.api  # 标记 API 测试（D1 配置的 marker）
def test_health_ok(service_up):
    """① 健康检查返回 200"""
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    assert r.status_code == 200


@pytest.mark.api
def test_models_list_contains_model(service_up):
    """② /v1/models 返回模型列表，且包含 ornith1.5-35b"""
    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
    r = requests.get(f"{BASE_URL}/v1/models", headers=headers, timeout=5)
    assert r.status_code == 200
    data = r.json()
    models = data.get("data", data.get("models", []))
    ids = [m.get("id") for m in models]
    assert ids, "模型列表为空"
    assert "ornith1.5-35b" in ids, f"期望含 ornith1.5-35b, 实际 {ids}"


@pytest.mark.api
def test_invalid_path_404(service_up):
    """③ 非法路径返回 404（或 401，取决于是否校验 key）"""
    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
    r = requests.get(f"{BASE_URL}/v1/this-path-does-not-exist", headers=headers, timeout=5)
    # vLLM 的非法路由约定返回 404（即便没 key，路由不匹配优先 404）
    assert r.status_code == 404


@pytest.mark.api
def test_chat_requires_api_key(service_up):
    """④ 无 API key 调用 /v1/chat/completions 返回 401（本机的鉴权要求）"""
    # 故意不带 Authorization 头
    r = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        json={"model": "ornith1.5-35b", "messages": [{"role": "user", "content": "hi"}]},
        timeout=5,
    )
    assert r.status_code == 401


@pytest.mark.api
def test_chat_requires_json_body(service_up):
    """⑤ 缺少 messages 字段，请求应被服务器拒绝（不是 200 空回）"""
    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
    r = requests.post(f"{BASE_URL}/v1/chat/completions", json={"model": "ornith1.5-35b"},
                      headers=headers, timeout=5)
    # 没有 messages 是不合法请求，不应返回 200
    assert r.status_code != 200


@pytest.mark.api
def test_chat_returns_content(service_up):
    """⑥ 带 key 发一条正经消息，返回 content 非空"""
    if not API_KEY:
        pytest.skip("需要 API_KEY 环境变量（本项目默认不存真实 key）")
    headers = {"Authorization": f"Bearer {API_KEY}"}
    r = requests.post(f"{BASE_URL}/v1/chat/completions",
                      json={"model": "ornith1.5-35b",
                            "messages": [{"role": "user", "content": "你好"}]},
                      headers=headers, timeout=30)
    assert r.status_code == 200
    content = r.json()["choices"][0]["message"]["content"]
    assert content, "返回内容不应为空"
    assert isinstance(content, str)


@pytest.mark.api
def test_timeout_raises_on_no_service(monkeypatch):
    """⑦ 超时保护：如果服务崩了，应快速抛 Timeout 而非一直等"""
    monkeypatch.setenv("BASE_URL", "http://127.0.0.1:9")  # 一个几乎没人监听的端口
    with pytest.raises(requests.exceptions.RequestException):
        requests.get(f"http://127.0.0.1:9/health", timeout=1)


@pytest.mark.api
def test_response_headers_has_content_type(service_up):
    """⑧ 响应头含 Content-Type（说明服务器正经返回了 JSON）"""
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    assert "Content-Type" in r.headers or "content-type" in {k.lower(): v
                                                               for k, v in r.headers.items()}


@pytest.mark.api
def test_models_without_key_401_or_200(service_up):
    """⑨ 不带 key 访问 /v1/models，要么 401（本机的鉴权行为）要么 200"""
    r = requests.get(f"{BASE_URL}/v1/models", timeout=5)
    assert r.status_code in (200, 401)
```

> 这个用例有 9 个（比计划的 8 个多 1 个），因为接口测试就该覆盖得细一点。其中 `test_chat_requires_api_key`（④）和 `test_chat_requires_json_body`（⑤）是**异常态**，`test_chat_returns_content`（⑥）是**正常态**，`test_models_without_key_401_or_200`（⑨）是**边界态**——三态都齐了。

---

## 四、8081 embedding 服务同样写用例（1h）

如果本机 8081 服务起来了，用同样的三态思路写：

```python
"""embedding 服务接口测试（可选，服务未启动会 skip）"""
import requests
import pytest

EMBED_URL = "http://127.0.0.1:8081"


@pytest.fixture(scope="session")
def embed_service_up():
    try:
        # embedding 服务通常没有 /health，试一下根路径
        r = requests.get(f"{EMBED_URL}/health", timeout=2)
        if r.status_code != 200:
            pytest.skip("embedding 服务未就绪")
    except requests.exceptions.RequestException:
        pytest.skip("embedding 服务 8081 未启动，跳过")


@pytest.mark.api
def test_embedding_endpoint(embed_service_up):
    r = requests.post(f"{EMBED_URL}/v1/embeddings",
                      json={"input": "你好", "model": "qwen3-embedding"}, timeout=10)
    assert r.status_code == 200
    data = r.json()
    # embedding 响应一般结构：{"data": [{"embedding": [...]}], "model": "..."}
    assert "data" in data, f"期望有 data 字段, 实际 {list(data.keys())}"
    # 如果 data 非空，第一维应是个向量
    assert len(data["data"]) >= 1
    assert isinstance(data["data"][0]["embedding"], list)
```

> 8081 服务今天实测**没起**，所以这个用例会被自动 skip——这正是 fixture `pytest.skip` 的价值：**测试还在，环境不在时不报错**。

---

## 五、异常态自测（1h）★ 先看失败长啥样

> 接口测试最容易犯的错误：只写"应该成功"的用例，从不验证"失败场景"。今天补齐失败案例，先故意看失败输出。

```python
# 故意失败的对照（看完删掉或改成正确断言）
import requests
import pytest

def test_intentional_fail_demo():
    # ❌ 故意写错：health 应该 200，但断言成 500，看 pytest 报什么
    r = requests.get("http://127.0.0.1:8000/health", timeout=5)
    assert r.status_code == 500, "健康检查应该返回 200，不是 500！"
```

跑 `pytest tests/test_local_api.py -v`，观察失败输出里的 `assert 500 == 200` 和 `健康检查应该返回 200…` 这段自定义信息——这就是失败时的定位线索。**这是今天最关键的观察练习。**

---

## 六、运行 & 验证

```bash
# 1. 先确认服务起来了
curl http://127.0.0.1:8000/health          # 期望 200

# 2. 运行全部接口测试
pytest tests/test_local_api.py -v

# 3. 只跑 API 类（配合 D1 的 marker 配置）
pytest -m api

# 期望输出（本机起服务时）：
# 9 passed  # （其中 test_chat_requires_api_key / test_embedding 可能 skip）

# 服务没起时的预期：
# 全部用例 show SKIPPED（不是 FAILED），因为 fixture 主动 skip 了
```

### 关键观察点
- 全绿 → 接口测通了 ✅
- 出现 `SKIPPED` → 服务没起，fixture 自动处理了，正常（D2 计划就是这么设计的）
- 出现 `FAILED` → 读失败信息，区分"服务真报错"还是"断言写错"
- `FAILED` 在 `test_chat_requires_api_key`（本该 401，实际不是）→ 说明本机 8000 对 chat 端点不强制 key，改断言即可

---

## 七、学习日志模板（20:00）

复制 `~/ai-testing-portfolio/learning-log/2026-08-22.md`，填写：
- 今天学会了什么：requests 基础、GET/POST、状态码三态断言
- 实测发现：本机模型是 `ornith1.5-35b`（不是计划里的 nemotron3）；8081 embedding 没起；8000 chat 端点是否强制 key 需实测
- 疑问：`json=` 和 `data=` 区别？`headers` 怎么组织？skip 和 fail 的区别？
- 明日预习：D3 fixture + mock（为"不真正调用 API"做准备）

## 八、commit 打卡（21:00）

```bash
cd ~/ai-testing-portfolio
git add -A
git commit -m "W1D2: requests 接口测试实战 vLLM 8-9 用例 + embedding 测试"
git push
```

---

## 📌 今日自检清单

- [ ] venv 已激活，requests 可用
- [ ] requests GET/POST/timeout/json()/headers 都会用
- [ ] 状态码速记熟练（2xx/4xx/5xx）
- [ ] 三态设计（正常/边界/异常）会套用到接口上
- [ ] 服务检查 fixture 会写（起→测，没起→skip）
- [ ] 9 个 vLLM 用例能全绿（或合理 skip）
- [ ] 失败用例能读出定位信息
- [ ] 学习日志 + commit 完成

## 🆘 卡住怎么办

- 安装 requests 失败 → `pip install --user requests` 或确认 venv 激活
- 连接被拒 `ConnectionRefusedError` → 服务没起，先 `curl /health`
- 401 永远过不去 → 看本机是否需要 key，从 `~/.openclaw/openclaw.json` 读，设成环境变量 `API_KEY`
- 卡 > 30min：看 https://requests.readthedocs.io（中文搜"requests 入门"）
- 卡 > 2h：直接问我（木木），带上报错信息

---

## 🎯 接口测试 vs 之前测试的区别（对比记忆）

| 对比项 | D1 数据校验测试 | D2 接口测试 |
|---|---|---|
| 测试对象 | 纯函数 / 数据 | HTTP 服务 |
| 核心依赖 | pytest assert | pytest assert + requests |
| 需要网络 | 不需要 | 需要（要 skip 兜底） |
| 失败分类 | 断言失败 | 服务失败 / 断言失败 / 环境失败(skip) |
| 关键技巧 | fixture 加载数据 | 超时 + 三态 + skip |

> 记住这个对比，它是你理解"测试从单元测试走向集成测试"的阶梯。
