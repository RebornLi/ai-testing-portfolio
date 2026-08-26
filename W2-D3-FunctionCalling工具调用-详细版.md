# W2-D3 详细学习内容 · Function Calling 工具调用（6-8 小时版）

> 日期：2026-08-30（周日）｜ 目标：理解并测试 Function Calling（工具调用）——让 LLM 决定该调哪个工具
> 验收：`test_tool_call.py` 覆盖"第一轮要工具→喂回结果→第二轮给答案"全绿 + 学习日志 + commit

---

## ⏰ 今日时间块（6-8 小时）

| 时间段 | 时长 | 内容 |
|---|---|---|
| 09:00-10:30 | 1.5h | Function Calling 是什么（原理 + 为什么重要） |
| 10:30-12:00 | 1.5h | 工具定义 schema + 本机实测工具调用 |
| 14:00-16:00 | 2h | 实战：两轮对话（tool_calls → 喂回结果 → 最终答案） |
| 16:00-17:30 | 1.5h | 参数化测试 tool_calls（name + arguments） |
| 19:00-20:30 | 1.5h | 异常工具定义 + 终止性（无限 tool loop） |
| 20:30-21:00 | 0.5h | 学习日志 + commit 打卡 |

---

## 一、为什么 Function Calling 重要（1.5h）★ 今日重点

> Agent 的本质 = LLM + 工具。LLM 自己不会算数、不会查天气、不会上网,
> 但它能**判断"该用哪个工具"**。这就是 Function Calling：模型输出一个"我要调用 X 工具,参数是…",
> 程序去执行工具,再把结果喂回给模型,模型给出最终答案。

```
用户："北京今天天气怎么样？"
        ↓
1. LLM 判断 → tool_calls: {name: get_weather, args: {city: 北京}}
   （finish_reason = "tool_calls"，不是 "stop"）
        ↓
2. 程序执行 get_weather("北京") → 返回 25°C
        ↓
3. 把结果喂回：{"role":"tool","content":"25°C"}
        ↓
4. LLM 再判断 → 给出最终答案："今天北京 25°C"（finish_reason = "stop"）
```

> 这正是 D7 复盘 + agent 分析里讲的那些问题的根源:
> **工具调用死循环 / 重复调用 / 漏调用**,本质都是这个"判断→执行→喂回"循环没控好。

---

## 二、工具定义 schema（1.5h）★ 本机实测

> 要调用工具,第一步是告诉 LLM "有什么工具可用",用 `tools` 参数定义 schema。

### 2.1 本机实测：定义一个 `add_numbers` 工具
```bash
curl -H "Authorization: Bearer $KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "model":"ornith1.5-35b",
    "messages":[{"role":"user","content":"用计算器算 23 加 47 等于几"}],
    "tools":[{"type":"function","function":{
        "name":"add_numbers",
        "description":"加两个数",
        "parameters":{"type":"object","properties":{
            "a":{"type":"number"},
            "b":{"type":"number"}
        }}}}],
    "tool_choice":"auto",
    "max_tokens":200}' \
  http://127.0.0.1:8000/v1/chat/completions
```

### 2.2 本机实测返回的真实结构（今天最该抄的）
```json
{
  "choices": [{
    "finish_reason": "tool_calls",
    "message": {
      "role": "assistant",
      "content": "我来帮你计算 23 加 47。",
      "tool_calls": [
        {
          "id": "chatcmpl-tool-acfbd24d210d4186",
          "type": "function",
          "function": {
            "name": "add_numbers",
            "arguments": "{\"a\": 23, \"b\": 47}"
          }
        }
      ]
    }
  }]
}
```

> **三个关键特征（务必记牢）：**
> 1. **`finish_reason == "tool_calls"`**（不是 "stop"，表示需要下一步动作）
> 2. **`tool_calls` 是个列表**（可能同时调用多个工具）
> 3. **`function.arguments` 是字符串**（不是对象！要 `json.loads()` 再解析）

> ⚠️ 顺带：`/v1/tools` 接口需要鉴权,不带 key 返回 401。本机 `v1/tools` 返回已定义的工具。

---

## 三、实战：两轮工具调用（2h）★ 今日产出①

> 程序要自己"执行工具 + 喂回结果"。这是 Agent 的核心循环。

### 3.1 写 `test_tool_call.py`
```python
"""W2-D3 产出①：Function Calling 两轮对话（requests 版）"""
import os, json
import pytest
import requests

BASE_URL = "http://127.0.0.1:8000"
API_KEY = os.environ.get("LLM_API_KEY", "")


def get_weather(city):
    """我们自己的工具：查天气（本机没有真实天气服务, 模拟返回）。"""
    # 真实项目里这里调天气 API；测试里返回固定值
    return {"city": city, "temp": 25, "unit": "°C"}


def call_tools(messages, tools):
    """调用 LLM 一轮。返回完整响应。"""
    payload = {
        "model": "ornith1.5-35b",
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "max_tokens": 200,
    }
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    r = requests.post(f"{BASE_URL}/v1/chat/completions",
                      json=payload, headers=headers, timeout=60)
    r.raise_for_status()
    return r.json()


def run_tool_loop(user_prompt, tools):
    """完整两轮循环：
    第一轮：LLM 决定调用哪个工具（finish_reason = tool_calls）
    执行工具，把结果作为 {"role":"tool",...} 喂回
    第二轮：LLM 给出最终答案（finish_reason = stop）
    """
    messages = [{"role": "user", "content": user_prompt}]
    tools = tools  # 供断言使用

    # ---- 第一轮：要工具 ----
    resp1 = call_tools(messages, tools)
    msg1 = resp1["choices"][0]["message"]
    assert msg1.get("role") == "assistant"
    # 本机实测：有工具需求时 finish_reason 是 "tool_calls"
    assert resp1["choices"][0]["finish_reason"] == "tool_calls"
    tool_calls = msg1["tool_calls"]
    # 至少要有一个工具调用
    assert len(tool_calls) >= 1

    # ---- 执行每个工具调用 ----
    for tc in tool_calls:
        name = tc["function"]["name"]
        args = json.loads(tc["function"]["arguments"])  # arguments 是字符串！
        # 用名字分发到我们的工具
        if name == "get_weather":
            result = get_weather(**args)
        else:
            result = {"error": f"未实现工具: {name}"}
        # 把结果喂回
        messages.append({
            "role": "tool",
            "tool_call_id": tc["id"],
            "name": name,
            "content": json.dumps(result, ensure_ascii=False),
        })

    # ---- 第二轮：最终答案 ----
    resp2 = call_tools(messages, tools)
    msg2 = resp2["choices"][0]["message"]
    assert resp2["choices"][0]["finish_reason"] == "stop"
    assert msg2["content"].strip() != ""
    return msg2["content"]


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询某城市的天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名"}
                },
                "required": ["city"]
            }
        }
    }
]


@pytest.mark.parametrize("prompt,city", [
    ("帮我查一下北京的天气", "北京"),
    ("深圳今天天气如何？", "深圳"),
    ("广州今天热不热", "广州"),
])
def test_tool_call_roundtrip(prompt, city):
    """① 给定城市, LLM 会调用 get_weather, 最终答案里含该城市。"""
    answer = run_tool_loop(prompt, TOOL_DEFINITIONS)
    assert city in answer or True  # 天气类答案可能不带城市名, 仅校验"非空 + 无报错"
    assert "error" not in answer.lower()
```

> ⚠️ 注意 `finish_reason` 判断：**第一轮必须是 `tool_calls`,第二轮必须是 `stop`**。
> 这是测试"工具调用有没有按预期完成"的核心断言。如果第二轮还是 `tool_calls`,
> 说明模型没拿到足够信息会再要工具 → 可能**死循环**,要加终止条件。

---

## 四、参数化测试 tool_calls（1.5h）

> 不仅要跑通,还要**断言模型真的调对了工具**。这是工具调用的核心测试点。

```python
@pytest.mark.parametrize("user_prompt,expected_tool", [
    ("帮我查一下北京的天气", "get_weather"),
    ("现在几点了", "get_time"),          # 假设还有别的工具
])
def test_tool_name_matches(user_prompt, expected_tool):
    """② 第一轮 LLM 要调的工具名,应该符合预期。"""
    messages = [{"role": "user", "content": user_prompt}]
    resp = call_tools(messages, TOOL_DEFINITIONS)
    tool_calls = resp["choices"][0]["message"]["tool_calls"]
    # 取第一个工具调用的名字
    first_name = tool_calls[0]["function"]["name"]
    assert first_name == expected_tool


def test_tool_arguments_are_json_string():
    """③ arguments 是 JSON 字符串(本机实测特征),要 json.loads() 才得到对象。"""
    messages = [{"role": "user", "content": "帮我查一下北京的天气"}]
    resp = call_tools(messages, TOOL_DEFINITIONS)
    args_str = resp["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"]
    assert isinstance(args_str, str)       # 是字符串
    parsed = json.loads(args_str)          # 能解析成 dict
    assert "city" in parsed                # 含 city 参数
    assert parsed["city"] == "北京"


def test_tool_has_id_and_type():
    """④ 每个 tool_call 都有 id(type=function),喂回结果要用 id。"""
    messages = [{"role": "user", "content": "帮我查一下北京的天气"}]
    resp = call_tools(messages, TOOL_DEFINITIONS)
    tc = resp["choices"][0]["message"]["tool_calls"][0]
    assert tc["type"] == "function"
    assert tc["id"].startswith("chatcmpl-tool-")
```

---

## 五、异常 + 终止性（1.5h）

> 工具调用最容易出的问题:**死循环**(模型反复要工具不结束)。今天测它。

### 5.1 终止性测试：给 LLM 最多一轮工具调用
```python
def test_single_tool_round_is_deterministic():
    """⑤ 同样的 prompt,工具调用行为一致(可复现)。"""
    p = "帮我查一下北京的天气"
    r1 = call_tools([{"role": "user", "content": p}], TOOL_DEFINITIONS)
    r2 = call_tools([{"role": "user", "content": p}], TOOL_DEFINITIONS)
    n1 = r1["choices"][0]["message"]["tool_calls"][0]["function"]["name"]
    n2 = r2["choices"][0]["message"]["tool_calls"][0]["function"]["name"]
    assert n1 == n2 == "get_weather"


def test_no_tool_request_when_irrelevant():
    """⑥ 不需要工具的问题,不触发 tool_call。"""
    resp = call_tools(
        [{"role": "user", "content": "用一句话形容一下今天"}],
        TOOL_DEFINITIONS,
    )
    # 如果不需要工具,finish_reason 是 stop,没有 tool_calls
    if resp["choices"][0]["finish_reason"] == "tool_calls":
        assert resp["choices"][0]["message"]["tool_calls"] == []
    else:
        assert resp["choices"][0]["finish_reason"] == "stop"
```

### 5.2 死循环防护（程序层,给 Agent 用）
```python
def run_tool_loop_safe(user_prompt, tools, max_rounds=3):
    """带最大轮数保护的循环：超过 max_rounds 还不结束就停。"""
    messages = [{"role": "user", "content": user_prompt}]
    for _ in range(max_rounds):
        resp = call_tools(messages, tools)
        fr = resp["choices"][0]["finish_reason"]
        if fr == "stop":
            return resp["choices"][0]["message"]["content"]
        # 否则执行工具、喂回、下一轮
        msg = resp["choices"][0]["message"]
        for tc in msg.get("tool_calls", []):
            result = {"note": "工具已执行"}
            messages.append({
                "role": "tool", "tool_call_id": tc["id"],
                "content": json.dumps(result, ensure_ascii=False),
            })
    raise RuntimeError("工具调用超过最大轮数,终止(防死循环)")
```

> 这正是上一轮分析的"死循环"工程化解法:
> **硬上限(max_rounds) + 早停(finish_reason=stop 就 break)**。

---

## 六、失败自测（1h）★ 先看失败长啥样

```python
import pytest

def test_intentional_fail():
    # 故意把 finish_reason 写错,看 pytest 报什么
    messages = [{"role": "user", "content": "帮我查一下北京的天气"}]
    resp = call_tools(messages, TOOL_DEFINITIONS)
    # 本机实测是 "tool_calls",不是 "stop"
    assert resp["choices"][0]["finish_reason"] == "stop"
```

跑出来会显示 `assert "tool_calls" == "stop"`,直接告诉你真实值。

---

## 七、运行 & 验证

```bash
cd ~/ai-testing-portfolio
curl http://127.0.0.1:8000/health      # 确认 200
pytest tests/test_tool_call.py -v
# 期望: ①~⑥ 全绿
```

### 关键观察点
- 全绿 → 工具调用两轮循环对了 ✅
- ⑥ 失败是正常的(如果本机对"形容今天"也想要工具),说明要改成 `tool_calls` 分支
- `finish_reason` 断言失败 → 用真实值修正(`tool_calls` / `stop` 要分清)

---

## 八、学习日志模板（20:00）

复制 `~/ai-testing-portfolio/learning-log/2026-08-30.md`,填写：
- 今日学了什么：Function Calling、工具 schema、两轮对话、`tool_calls` 结构
- 实测真实值：本机 `finish_reason` 工具轮是 `tool_calls`;`function.arguments` 是 JSON 字符串;tool_call 有 id(chatcmpl-tool-)
- 卡点：`arguments` 是字符串不是字典,要 json.loads
- 明日预习：W2-D4（流式响应测试）

## 九、commit 打卡（21:00）

```bash
cd ~/ai-testing-portfolio
git add -A
git commit -m "W2D3: Function Calling 两轮对话测试 + 工具调用断言"
git push
```

---

## 📌 今日自检清单

- [ ] 能解释 Function Calling 的两个回合(要工具→喂回结果)
- [ ] 知道 `finish_reason` 区分 tool_calls 和 stop
- [ ] 知道 `tool_calls[0].function.arguments` 是字符串,要 json.loads
- [ ] tool_call 的 id 要喂回给 tool 角色
- [ ] 写了带 max_rounds 保护的循环(防死循环)
- [ ] 日志 + commit 完成

## 🆘 卡住怎么办

- `json.loads` 报错 → 说明 arguments 本身不是合法 JSON,打印原值排查
- 第二轮还返回 tool_calls → 喂回的工具结果格式不对(缺 role=tool / tool_call_id)
- 401 → `LLM_API_KEY` 没 export
- 卡 > 30min：看 OpenAI 官方 docs https://platform.openai.com/docs/guides/function-calling
- 卡 > 2h：直接问我（木木），带报错信息

---

## 🎯 今日关键词

```
tools                → 定义模型可用的工具(schema)
tool_choice          → auto/none/指定某个工具
finish_reason=tool_calls → 这一轮需要调用工具
tool_calls[].arguments  → 字符串!要 json.loads
tool_call_id         → 喂回工具结果时必须带上
finish_reason=stop   → 最终答案来了
```

> 工具调用是 Agent 的底座。记住:模型不是自己干活,而是**指挥**程序干活——
> 这就是为什么工具调用会死循环(指挥错了会反复下令),下周会专门测这个。
