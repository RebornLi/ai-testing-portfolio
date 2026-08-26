# W2-D1 详细学习内容 · 认识 LLM API（6-8 小时版）

> 日期：2026-08-28（周五）｜ 目标：认识 LLM API，用本地真实服务 vLLM(:8000) 跑出第一个对话
> 验收：能发一次完整 chat completion + 拿到 usage/流式响应 + 学习日志 + commit

---

## ⏰ 今日时间块（6-8 小时）

| 时间段 | 时长 | 内容 |
|---|---|---|
| 09:00-10:30 | 1.5h | LLM API 是什么（OpenAI 兼容协议） |
| 10:30-12:00 | 1.5h | 核心参数详解（temperature/max_tokens/stream 等） |
| 14:00-16:00 | 2h | 实战：用 httpx 连本地 vLLM 跑第一次对话 |
| 16:00-17:30 | 1.5h | 流式响应(stream)实战 + 解析 |
| 19:00-20:30 | 1.5h | 真实响应结构拆解（choices/usage/finish_reason） |
| 20:30-21:00 | 0.5h | 学习日志 + commit 打卡 |

---

## 一、LLM API 是什么（1.5h）

### 1.1 一句话理解
> LLM API = 把大模型当"云端函数"调用：发一段对话，返回一段回答。你的本机 vLLM 服务就是这个"云端"。

```
你的程序  →  HTTP POST /v1/chat/completions  →  LLM 服务  →  返回 JSON
```

### 1.2 OpenAI 兼容协议（为什么叫"兼容"）
本机 `http://127.0.0.1:8000` 跑的是 **vLLM**，它的接口**和 OpenAI 完全对齐**。这意味着：
- 写 OpenAI 官方文档看到的用法，换成本机只改 `base_url` 就能跑
- 用 `openai` 库、`requests`、`httpx` 都能调

### 1.3 本机环境自检（重要，先确认服务在跑）
```bash
curl http://127.0.0.1:8000/health
# 期望 200

curl http://127.0.0.1:8000/v1/models
# 期望返回模型列表
```

**本机实测（2026-08-28 记录）：**
```json
{
  "object": "model-list",
  "data": [{"object": "model", "id": "ornith1.5-35b"}]
}
```
> ⚠️ 计划里写的"nemotron3"已不在本机。本机模型是 **`ornith1.5-35b`**（一个 thinking 模型，后面会讲到 reasoning 字段）。**写测试要用真实模型名，别照抄计划。**

---

## 二、核心参数详解（1.5h）★ 今日重点

> 参数 = 你给模型的"使用说明"。今天吃透 6 个最关键的。

### 请求体结构（chat completion）
```python
payload = {
    "model": "ornith1.5-35b",                 # 用哪个模型
    "messages": [                              # 对话内容（按顺序）
        {"role": "system", "content": "你是一个友好的助手。"},
        {"role": "user", "content": "你好"},
    ],
    "temperature": 0.7,                         # 随机性 0-2
    "max_tokens": 256,                          # 最多生成多少 token
    "stream": False,                            # 是否流式输出
}
```

### 6 个核心参数（配本机实测值）

| 参数 | 含义 | 范围 | 本机实测 |
|---|---|---|---|
| `model` | 选模型 | 字符串 | `ornith1.5-35b` |
| `messages` | 对话轮次 | 列表 | system/user/assistant |
| `temperature` | 创造性 | 0-2 | 默认 0.7；越高越发散 |
| `max_tokens` | 最大输出长度 | ≥1 | 设 50 时 finish_reason=length |
| `stream` | 流式返回 | true/false | true → chunk 分批 |
| `stop` | 停止条件 | 字符串/列表 | 命中即停 |

### 深入理解 temperature
```
temperature=0.0  → 确定性最高（同一输入同一输出），适合评测
temperature=0.7  → 平衡，默认
temperature=1.0+ → 越来越随机，适合创意写作
```
> 评测场景（今天最重要）：**temperature 设 0**，保证结果可复现。同一个输入反复调用得到同样输出，测试才稳。

### 深入理解 max_tokens 与 finish_reason
```
max_tokens 设太小 → 回答被"拦腰截断"，finish_reason 变成 "length"
```
**本机实测**：`max_tokens=50` 时，`finish_reason = "length"`（说明确实是 token 用满了被截断）。`finish_reason` 常见取值：
- `"stop"` —— 自然说完
- `"length"` —— 超长被 max_tokens 截断
- `"function_call"` —— 触发了函数调用（下周讲）
- `"content_filter"` —— 内容被过滤

---

## 三、实战：第一个 chat completion（2h）★ 今日产出①

> roadmap 建议"LLM API 走 httpx"（更现代）。但今天先用 `requests`（你已学过），再补 httpx 版本。

### 3.1 安装（venv 里）
```bash
cd ~/ai-testing-portfolio
pip install requests httpx pytest
```

### 3.2 API Key 管理（铁律：不要硬编码！）
> 你的 key 在 `~/.openclaw/openclaw.json`。测试脚本要**从环境变量读**，绝不写死在代码里。

```bash
# 先看 key 在哪个键（别直接打印）
python3 -c "import json;d=json.load(open('/home/mushan/.openclaw/openclaw.json'));print(list(d.get('models',{}).get('providers',{}).keys()))"
# 找到后，导出成环境变量（本会话用）
export LLM_API_KEY=sk-xxxxxx
```

### 3.3 写 `test_llm_basic.py`（requests 版）
```python
"""W2-D1 产出①：和本机 vLLM 跑第一次对话（requests 版）"""
import os
import requests

BASE_URL = "http://127.0.0.1:8000"          # 本机 vLLM
API_KEY = os.environ.get("LLM_API_KEY", "")  # 从环境变量读


def chat(prompt, max_tokens=100, temperature=0.0):
    """调用 LLM 一次，返回回答内容。"""
    payload = {
        "model": "ornith1.5-35b",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    r = requests.post(f"{BASE_URL}/v1/chat/completions",
                      json=payload, headers=headers, timeout=60)
    r.raise_for_status()          # 非 2xx 抛异常（自动处理 401/404/500）
    return r.json()


if __name__ == "__main__":
    resp = chat("你好")
    print("返回内容:", resp["choices"][0]["message"]["content"])
```

### 3.4 跑一下，看真实结果
```bash
cd ~/ai-testing-portfolio
python3 test_llm_basic.py
```

**本机实测输出（2026-08-28 记录）：**
```
返回内容:

你好！😊 有什么我可以帮你的吗
```

---

## 四、真实响应结构拆解（1.5h）★ 今天最重要的"地图"

> 理解响应长啥样，后面所有断言都建立在这张"地图"上。

### 4.1 完整响应（非流式）关键字段
```python
resp = chat("你好")
# resp 结构：
{
    "id": "chatcmpl-xxxx",         # 本次对话 ID
    "object": "chat.completion",   # 对象类型
    "created": 1787738655,         # 时间戳
    "model": "ornith1.5-35b",      # 用哪个模型
    "choices": [                   # 生成结果（默认 1 条）
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "\n\n你好！😊...",   # 答案正文
            },
            "finish_reason": "length",  # 为何结束（length/stop/...）
        }
    ],
    "usage": {                        # 用量（计费/性能关键）
        "prompt_tokens": 11,          # 输入 token
        "completion_tokens": 50,      # 生成 token
        "total_tokens": 61,           # 总计
    },
}
```

### 4.2 怎么取"答案正文"
```python
content = resp["choices"][0]["message"]["content"]
# 记住：choices[0] 是第一条，message.content 是正文
```

### 4.3 本机实测的几个坑（务必记牢）

| 现象 | 实测结果 | 怎么应对 |
|---|---|---|
| 本机模型叫啥 | `ornith1.5-35b`（不是 nemotron3） | 用真实模型名 |
| 是否返回 reasoning | **是**（有 `reasoning` 字段，约 71 字符） | 回答可能含"思考过程" |
| 回答开头 | 常有 `\n\n` 开头 | 断言时用 `strip()` 再比 |
| 不存在模型 | **404**，`error.message` 含 model 名 | `raise_for_status()` 自动抓 |
| 无 API key | **401** | 确认 key 已注入 |

---

## 五、流式响应实战（1.5h）★ 今日产出②

> 大模型回答是"边想边说"——流式就是把它说的每个词实时推给你。你手机里的对话界面就是这种体验。

### 5.1 流式 vs 非流式对比
| 对比 | 非流式(stream=false) | 流式(stream=true) |
|---|---|---|
| 返回方式 | 一次全给 | 分多个 chunk 推 |
| 响应类型 | `chat.completion` | `chat.completion.chunk` |
| 逐块内容 | 在 `message.content` | 在 `delta.content` |

### 5.2 本机流式实测（抓到的真实 chunk 结构）
```json
{"object":"chat.completion.chunk","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}
{"object":"chat.completion.chunk","choices":[{"index":0,"delta":{"reasoning":"用户"},"finish_reason":null}]}
{"object":"chat.completion.chunk","choices":[{"index":0,"delta":{"reasoning":"让我"},"finish_reason":null}]}
```
> 注意：本机模型流式时，**先返回 reasoning（思考过程），再返回 content**。`delta.content` 为空时可能在思考。

### 5.3 写流式调用（requests 版）
```python
def chat_stream(prompt, max_tokens=100):
    """流式调用：逐个块返回内容。"""
    payload = {
        "model": "ornith1.5-35b",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": True,
    }
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    full = ""
    with requests.post(f"{BASE_URL}/v1/chat/completions",
                       json=payload, headers=headers, stream=True, timeout=120) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            if line.startswith(b"data: "):
                data = line[6:]
                if data == b"[DONE]":
                    break
                chunk = json.loads(data)
                delta = chunk["choices"][0].get("delta", {})
                content = delta.get("content", "")
                full += content
                yield content          # 逐块产出
    yield ""
```

### 5.4 跑流式
```python
if __name__ == "__main__":
    print("流式输出:")
    for piece in chat_stream("用三个词描述今天", max_tokens=60):
        print(piece, end="", flush=True)
    print()
```

---

## 六、异常测试（1.5h）★ 先看失败长啥样

> 接口测试要测"应该报错"的场景。今天实测 3 个异常态。

```python
import pytest
import requests

def test_not_exist_model_404():
    """不存在的模型 → 404"""
    r = requests.post(f"{BASE_URL}/v1/chat/completions",
                      json={"model": "不存在的模型",
                            "messages": [{"role": "user", "content": "hi"}]},
                      timeout=10)
    assert r.status_code == 404

def test_no_api_key_401():
    """不带 key → 401（本机实测）"""
    r = requests.post(f"{BASE_URL}/v1/chat/completions",
                      json={"model": "ornith1.5-35b",
                            "messages": [{"role": "user", "content": "hi"}]},
                      timeout=10)
    assert r.status_code == 401

def test_reasoning_field_exists():
    """本机模型返回 reasoning 字段（thinking 模型特征）"""
    resp = chat("你好")
    assert "reasoning" in resp["choices"][0]["message"]
```

---

## 七、运行 & 验证

```bash
cd ~/ai-testing-portfolio
# 1. 确认服务在跑
curl http://127.0.0.1:8000/health     # 期望 200

# 2. 跑测试
pytest test_llm_basic.py -v
# 期望：chat completion + 流式 + 3 个异常测试 全绿
```

### 关键观察点
- 全绿 → 你已经会和 LLM API 对话了 ✅
- 报错 401 → key 没注入（检查 `LLM_API_KEY` 环境变量）
- 报错 404 → 模型名写错（用真实名 `ornith1.5-35b`）
- `finish_reason = "length"` → 正常，说明 max_tokens 设小了

---

## 八、学习日志模板（20:30）

复制 `~/ai-testing-portfolio/learning-log/2026-08-28.md`，填写：
- 今日学了什么：LLM API 协议、核心参数、流式、响应结构
- 实测真实值：本机模型 ornith1.5-35b；usage = prompt + completion + total tokens；流式 chunk 先返回 reasoning
- 卡点：流式怎么用？reasoning 字段要不要过滤？
- 明日预习：W2-D2（参数化调用 + 响应校验）

## 九、commit 打卡（21:00）

```bash
cd ~/ai-testing-portfolio
git add -A
git commit -m "W2D1: 认识 LLM API + 首个 chat completion（本地 vLLM）"
git push
```

---

## 📌 今日自检清单

- [ ] 能解释 OpenAI 兼容协议（为什么本机接口能直接用）
- [ ] temperature 0 vs 1 的区别会讲
- [ ] max_tokens 与 finish_reason 的关系懂
- [ ] 能从 `choices[0].message.content` 取答案
- [ ] 能写一次非流式调用 + 一次流式调用
- [ ] 从环境变量读 key，不硬编码
- [ ] 知道本机模型名（ornith1.5-35b，不是 nemotron3）
- [ ] 日志 + commit 完成

## 🆘 卡住怎么办

- 401 → 检查 `LLM_API_KEY` 是否 `export` 了
- 404 → 用真实模型名 `ornith1.5-35b`
- 连接失败 → 服务没起，先 `curl /health` 确认
- 卡 > 30min：看 OpenAI 官方 docs（https://platform.openai.com/docs/api-reference/chat）
- 卡 > 2h：直接问我（木木），带报错信息

---

## 🎯 今日关键词速记

```
/health        → 服务自检（200=在跑）
/v1/models     → 列模型（本机: ornith1.5-35b）
/v1/chat/
  completions  → 对话（POST）
temperature    → 0=确定(评测用)，越高越随机
max_tokens     → 生成上限（太大→finish_reason=length）
stream         → 流式（chunk 分批）
choices[0]     → 取第一条答案
usage          → prompt/completion/total tokens
finish_reason  → length/stop/function_call
```

> 记住这张"地图"，下周所有 LLM 测试都建立在今天这张响应结构图上。
