# W1-D3 详细学习内容 · fixture + mock 进阶（6-8 小时版）

> 日期：2026-08-23（周日）｜ 目标：吃透 fixture 作用域，掌握 mock 技术，做第一个"本地分析工具 + 测试"
> 验收：`jd_stats.py` 工具正确 + `test_jd_stats.py` 5 用例绿 + `test_llm_parser.py` 不依赖真服务全绿 + 日志 + commit

---

## ⏰ 今日时间块（6-8 小时）

| 时间段 | 时长 | 内容 |
|---|---|---|
| 09:00-10:00 | 1h | fixture 回顾 + 作用域深讲（function/module/session + yield） |
| 10:00-11:30 | 1.5h | 实战：写 `jd_stats.py` 工具 + 测试（fixture 传数据） |
| 14:00-15:30 | 1.5h | mock 入门：monkeypatch 与 unittest.mock.patch |
| 15:30-17:00 | 1.5h | 实战：mock 模拟 LLM 响应（不调真服务）解析 choices |
| 19:00-20:00 | 1h | session 级 fixture 性能优化 + 失败自测 |
| 20:00-21:00 | 1h | 学习日志 + commit 打卡 |

---

## 一、fixture 作用域深讲（1h）★ 承上启下

> D1 我们用过最简单的 fixture（每个测试函数调用一次）。今天学**作用域**和 **yield teardown**——这是测试框架的进阶能力。

### 1.1 三个作用域对比

| scope | 触发时机 | 用在哪 |
|---|---|---|
| function（默认） | 每个测试函数各来一次 | 绝大多数情况（每个测试要隔离） |
| module | 每个测试文件加载一次 | 大文件加载一次、模块级初始化 |
| session | 整个会话只一次 | 重活（联网/大文件/连接池），省时间 |

```python
import pytest

@pytest.fixture(scope="session")      # 全会话只调用一次
def expensive_setup():
    print("setup 只跑一次！")          # 只打印一次
    yield "准备好的数据"
    print("teardown 也只跑一次")        # 收尾

def test_a(expensive_setup):
    assert expensive_setup == "准备好的数据"

def test_b(expensive_setup):            # 复用同一个，不再重跑
    assert expensive_setup.startswith("准备")
```

### 1.2 yield fixture（setup / teardown 一体）

```python
@pytest.fixture
def temp_file():
    import tempfile, os
    path = tempfile.mktemp(suffix=".txt")
    with open(path, "w") as f:
        f.write("seed")
    yield path              # ← yield 之后的代码是 teardown
    os.remove(path)         # ← 测试跑完自动清理
```

> 关键：**yield 前面的代码 = 准备（setup），yield 之后的代码 = 清理（teardown）**。测试函数拿到的是 yield 传的值。

### 1.3 作用域大小关系
```
session  >  module  >  function
（作用域越大，复用次数越多，共享风险越大）
```
> 默认用 function（隔离最好）；只有确实"太贵"才升级到 session。D1 提到过"大文件只加载一次是性能优化"——今天实战。

---

## 二、实战：写 jd_stats.py 工具（1.5h）★ 今日产出①

> 任务：写一个 JD 统计分析工具，能算 AI 占比、城市分布、含 AI 技能占比。这个工具会被测试"套数据"验证。

### 2.1 先创建项目结构（沿用 D1）

```bash
cd ~/ai-testing-portfolio/jd-validator
mkdir -p src tests
touch src/__init__.py
```

> 建 `src/__init__.py` 让这个目录变成 Python 包，测试里才能 `from src.jd_stats import ...`。

### 2.2 写 `src/jd_stats.py`

```python
"""W1-D3 产出①：JD 数据统计分析工具（纯函数，不依赖任何外部服务）"""
import json
from collections import Counter


def load_data(path: str = None):
    """读取 JD 数据（默认用项目内置的数据文件路径）。

    注意：测试时我们用 fixture 直接传数据，不依赖这个默认路径，
    这样工具才能"脱离真实文件也能被测试"。
    """
    if path is None:
        path = "data.json"      # 默认相对路径（真实运行时用）
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def ai_ratio(jobs: list) -> float:
    """AI 相关岗位占比（0-1）。判断标准：相关度字段 == 'AI相关'。"""
    if not jobs:
        return 0.0
    ai = sum(1 for j in jobs if j.get("相关度") == "AI相关")
    return round(ai / len(jobs), 4)


def city_distribution(jobs: list) -> Counter:
    """各城市岗位数量统计（Counter 对象）。"""
    return Counter(j.get("城市", "未知") for j in jobs)


def top_cities(jobs: list, n: int = 5) -> list:
    """城市岗位数量 TOP-N，返回 [(城市, 数量), ...]。"""
    return city_distribution(jobs).most_common(n)


def ai_related_skill_ratio(jobs: list) -> float:
    """含 'AI' 技能的岗位占比（简单估算：技能字符串含 'AI' 子串）。"""
    if not jobs:
        return 0.0
    has_ai = sum(1 for j in jobs if "AI" in (j.get("技能") or ""))
    return round(has_ai / len(jobs), 4)


if __name__ == "__main__":
    # 命令行直接跑：python src/jd_stats.py
    data = load_data()
    print(f"总岗位数: {len(data)}")
    print(f"AI 相关占比: {ai_ratio(data)}")
    print(f"含 AI 技能占比: {ai_related_skill_ratio(data)}")
    print(f"城市 TOP5: {top_cities(data)}")
```

### 2.3 先手动跑一下工具，拿到"正确答案"

```bash
cd ~/ai-testing-portfolio/jd-validator
python3 src/jd_stats.py
```

**本机实测真实值（先记住，等下测试要用）：**
```
总岗位数: 61
AI 相关占比: 0.7377
含 AI 技能占比: 0.3934
城市 TOP5: [('西安', 28), ('北京', 7), ('深圳', 5), ('成都', 5), ('上海', 2)]
```

> ⚠️ **为什么用真实值做断言**：测试不能"猜"数字。要么先跑出真实值写进去（今天的做法），要么用"恒等式"断言（如 AI 占比在 0~1 之间）。这里我们**先跑真实值，再断言等于它**——这是最稳妥的"已知正确答案"测试法。

---

## 三、测试 jd_stats.py（用 fixture 传数据）（接上）

创建 `tests/test_jd_stats.py`。关键是**用一个 fixture 传入已知数据**，这样测试不依赖真实 JSON 文件，且能控制输入。

```python
"""W1-D3 产出②：对 jd_stats.py 写 5 个测试用例
用 fixture 传入"已知正确答案"的数据，验证工具计算正确。
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from jd_stats import ai_ratio, city_distribution, top_cities, ai_related_skill_ratio

# 已知正确答案的样本数据（故意造简单数据，方便验证每个函数）
SAMPLE_JOBS = [
    {"职位": "AI 测试", "相关度": "AI相关", "城市": "北京", "技能": "AI 自动化"},
    {"职位": "AI 测试", "相关度": "AI相关", "城市": "北京", "技能": "AI 工具"},
    {"职位": "测试", "相关度": "低相关", "城市": "西安", "技能": "手工测试"},
]


def test_ai_ratio_matches_expected_value():
    """① AI 占比：3 条里 2 条 AI 相关 = 0.6667"""
    assert ai_ratio(SAMPLE_JOBS) == 0.6667


def test_ai_ratio_empty_jobs():
    """② 空数据应返回 0（不能除以 0）"""
    assert ai_ratio([]) == 0.0


def test_city_distribution_counts():
    """③ 城市统计：北京=2，西安=1"""
    dist = city_distribution(SAMPLE_JOBS)
    assert dist["北京"] == 2
    assert dist["西安"] == 1


def test_top_cities_returns_list_of_tuples():
    """④ TOP 城市返回 [(城市, 数量), ...]，且第一个最多"""
    result = top_cities(SAMPLE_JOBS, n=2)
    assert isinstance(result, list)
    assert result[0] == ("北京", 2)   # 北京最多


def test_ai_related_skill_ratio():
    """⑤ 含 AI 技能占比：3 条里 2 条含 'AI' = 0.6667"""
    assert ai_related_skill_ratio(SAMPLE_JOBS) == 0.6667
```

> 这套测试**完全不用真实 JD 文件**，因为 fixture 思想已经内化：我们直接喂"已知输入"。运行 `pytest tests/test_jd_stats.py -v`，期望 5 用例全绿。

### 3.1 进阶：用 session 级 fixture 只加载一次真实数据

> D1 的 `test_jd_data.py` 每个用例都加载 61 条 JD。今天改成 session 级——整个会话只加载一次。看性能意识的落地。

```python
import pytest

@pytest.fixture(scope="session")
def real_jobs():
    """session 级：真实 JD 数据只加载一次"""
    from jd_stats import load_data
    return load_data()

def test_real_ai_ratio(real_jobs):
    """⑥ 真实数据 AI 占比 = 0.7377（本机实测值）"""
    assert ai_ratio(real_jobs) == 0.7377

def test_real_top_city_is_xian(real_jobs):
    """⑦ 真实数据城市 TOP1 = 西安（28 个岗位）"""
    assert top_cities(real_jobs)[0] == ("西安", 28)

def test_real_has_many_cities(real_jobs):
    """⑧ 真实数据城市不止 1 个（分布合理）"""
    assert len(city_distribution(real_jobs)) > 5
```

---

## 四、mock 入门（1.5h）★ 今日重点

> **为什么需要 mock？** 测试不能依赖真实的外部服务（慢、不可控、可能收费）。mock 就是"伪造一个替身"，假装它返回了我们要的值，让我们的代码只测自己。

### 4.1 monkeypatch（pytest 内置）

```python
import pytest

# 真实的外部调用（慢/不可控）
def get_weather(city):
    return requests.get(f"https://api.weather.com?city={city}").json()["temp"]

# 用 monkeypatch 伪造 requests.get 的返回值
def test_weather_parser(monkeypatch):
    class FakeResp:
        def json(self):
            return {"temp": 25}
    # 把 requests.get 替换成"返回假数据"的函数
    monkeypatch.setattr("requests.get", lambda url: FakeResp())
    assert get_weather("西安") == 25
```

> `monkeypatch.setattr(目标, 新值)` —— 测试结束后**自动还原**，不用手动 restore。

### 4.2 unittest.mock.patch（上下文管理器）

```python
from unittest import mock
import requests

@mock.patch("requests.get")              # 把 requests.get 换成替身
def test_with_patch(fake_get):
    fake_get.return_value = type("R", (), {"json": lambda: {"temp": 25}})()
    assert get_weather("北京") == 25
    fake_get.assert_called_once()       # 断言"确实被调用了"
```

---

## 五、实战：mock 模拟 LLM 响应（1.5h）★ 今日产出③

> 场景：写一个"解析 LLM 响应"的函数，它需要拿到 `choices[0].message.content`。但我们**不真正调用 vLLM 服务**（D2 的测试对象），用 mock 伪造一个响应。

### 5.1 写解析函数 `src/llm_parser.py`

```python
"""W1-D3 产出③：LLM 响应解析函数（纯函数，便于测试"""
def parse_response(resp_dict: dict) -> str:
    """从 OpenAI 兼容的响应字典里提取模型回复内容。

    resp_dict 结构（OpenAI 风格）：
        {"choices": [{"message": {"content": "你好"}}]}
    返回 choices[0].message.content。
    """
    if not resp_dict.get("choices"):
        raise ValueError("响应里 choices 为空")
    message = resp_dict["choices"][0]["message"]
    content = message.get("content")
    if content is None:
        raise ValueError("返回内容 content 为空")
    return content


def summarize_messages(resp_dict: dict) -> dict:
    """提取响应的结构化信息（用于报告）。"""
    return {
        "content": parse_response(resp_dict),
        "n_choices": len(resp_dict.get("choices", [])),
    }
```

### 5.2 测试 `test_llm_parser.py`（关键：mock，不调真服务）

```python
"""W1-D3 产出④：LLM 响应解析测试（用 mock 伪造响应，不真正调用 :8000）"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import llm_parser

# 真实 LLM 响应长啥样（OpenAI 风格）
MOCK_LLM_RESPONSE = {
    "id": "chatcmpl-test",
    "object": "chat.completion",
    "choices": [
        {
            "message": {"role": "assistant", "content": "这是一段示例回复"},
            "finish_reason": "stop",
            "index": 0,
        }
    ],
}


def test_parse_returns_content():
    """① 解析出 content 字符串"""
    assert llm_parser.parse_response(MOCK_LLM_RESPONSE) == "这是一段示例回复"


def test_parse_empty_choices_raises():
    """② choices 为空应抛异常（不是返回空）"""
    try:
        llm_parser.parse_response({"choices": []})
        assert False, "空 choices 应抛出 ValueError"
    except ValueError:
        pass


def test_parse_with_multiple_choices():
    """③ 多 choices 时取第一个（index 0）"""
    resp = {"choices": [
        {"message": {"content": "第一个"}},
        {"message": {"content": "第二个"}},
    ]}
    assert llm_parser.parse_response(resp) == "第一个"


def test_llm_call_is_mocked_not_real(monkeypatch):
    """④ 核心：用一个 mock 函数替代真实的 requests.post，
    让它返回 MOCK 数据，验证"不真调服务也能跑通"。"""
    import requests
    called = {"n": 0}

    def fake_post(url, *args, **kwargs):
        called["n"] += 1
        # 返回一个假的 response 对象
        resp = type("Resp", (), {"json": lambda self: MOCK_LLM_RESPONSE})()
        return resp

    monkeypatch.setattr("requests.post", fake_post)

    # 模拟一个调用 LLM 的函数
    def call_llm(prompt):
        resp = requests.post("http://127.0.0.1:8000/v1/chat/completions",
                             json={"messages": [{"role": "user", "content": prompt}]})
        return llm_parser.parse_response(resp.json())

    result = call_llm("你好")
    assert result == "这是一段示例回复"
    assert called["n"] == 1      # 确认"调用确实发生"，但用的是替身

def test_llm_call_returns_real_service_skipped():
    """⑤ 如果想测真服务，需要 API_KEY + 服务在线；否则 skip（本默认不依赖真服务）"""
    import os
    if not os.environ.get("API_KEY") or not _service_up():
        from pytest import skip
        skip("需要真实服务与 API_KEY（本用例为离线测试）")


def _service_up():
    """检查服务是否起来（供 skip 判断）。"""
    try:
        import requests
        return requests.get("http://127.0.0.1:8000/health", timeout=2).status_code == 200
    except Exception:
        return False


def test_summarize_structures_response():
    """⑥ 结构化提取：content + choices 数量"""
    summary = llm_parser.summarize_messages(MOCK_LLM_RESPONSE)
    assert summary["content"] == "这是一段示例回复"
    assert summary["n_choices"] == 1
```

> 这套测试里有 **`monkeypatch` 伪造 `requests.post`**（④），这是今天最关键的 mock 实战：即使本机 vLLM 没起，或你想测"如果模型返回了 X 会怎样"，都能mock。这是专业测试和新手的核心分水岭。

---

## 六、session 级 fixture 性能优化（1h）

### 6.1 对比：function vs session 加载大数据

```python
# ❌ 慢：每个测试都重新加载（假设大文件）
@pytest.fixture
def big_data_slow():
    return load_big_file()          # 每个用例重加载

# ✅ 快：整个会话只加载一次
@pytest.fixture(scope="session")
def big_data_fast():
    return load_big_file()          # 只加载一次
```

### 6.2 实战：对比两种加载速度

```python
import time
import pytest
from jd_stats import load_data

@pytest.fixture
def load_once():
    return load_data()

@pytest.fixture(scope="session")
def load_once_session():
    return load_data()

def test_speed_function(load_once):
    assert len(load_once) == 61

def test_speed_session(load_once_session):
    assert len(load_once_session) == 61

# 加计时观察两种方式的差异（用 -s 看 print）
def test_timing_comparison():
    t0 = time.time()
    load_data()
    print(f"\n函数级加载耗时: {time.time()-t0:.4f}s")
```

> 数据小时看不出差别，但大文件或联网时，session 级 fixture 能省 80%+ 时间。这就是"性能优化"的落地。

---

## 七、运行 & 验证

```bash
cd ~/ai-testing-portfolio/jd-validator
# 先跑工具看真实值
python3 src/jd_stats.py
# 运行全部测试
pytest tests/ -v
# 期望：test_jd_stats.py(5-8 用例) + test_llm_parser.py(6 用例) 全绿
# 不依赖真服务（mock + 已知正确答案）
```

### 关键观察
- 全绿 → 工具和 mock 测试都通过了 ✅
- `test_llm_call_is_mocked_not_real` 用了 monkeypatch，**没连 :8000**，离线也能绿
- 若某个用例 FAIL → 大概率是"已知正确答案"写错（回到 2.3 的真实值核对）

---

## 八、学习日志模板（20:00）

复制 `~/ai-testing-portfolio/learning-log/2026-08-23.md`，填写：
- 今天学到了：fixture 三作用域、yield teardown、monkeypatch / mock.patch、mock 不调真服务
- 实测真实值：AI 占比 0.7377、城市 TOP1 西安 28、含 AI 技能占比 0.3934
- 疑问：monkeypatch 和 mock.patch 区别？yield fixture 什么时候该用？session fixture 怎么失败？
- 明日预习：D4 参数化（一个函数测 100 组数据）

## 九、commit 打卡（21:00）

```bash
cd ~/ai-testing-portfolio
git add -A
git commit -m "W1D3: jd_stats 分析工具 + mock 测 LLM 解析（无依赖真服务）"
git push
```

---

## 📌 今日自检清单

- [ ] fixture 三作用域能解释（function/module/session）
- [ ] yield fixture 的 setup/teardown 会写
- [ ] monkeypatch.setattr 用法掌握
- [ ] unittest.mock.patch 会用作上下文管理器
- [ ] jd_stats.py 工具输出正确值
- [ ] 5 个 jd_stats 测试全绿
- [ ] mock 测 LLM 解析不依赖真服务
- [ ] 日志 + commit 完成

## 🆘 卡住怎么办

- `ImportError: No module named 'jd_stats'` → 确认 `sys.path.insert` 指向 src 目录
- 测试报 `AssertionError` → 核对真实值（先 `python3 src/jd_stats.py` 看输出）
- mock 没生效 → 检查 `monkeypatch.setattr` 的目标字符串是否正确（如 `"requests.post"`）
- 卡 > 30min：查 pytest 文档 + mock 文档（https://docs.python.org/3/library/unittest.mock.html）
- 卡 > 2h：直接问我（木木），带上报错信息

---

## 🎯 三者对比：测试进阶之路

| 对比项 | D1 数据校验 | D2 接口测试 | D3 工具+mock |
|---|---|---|---|
| 核心概念 | assert 体系 | requests 三态 | fixture 复用 + mock |
| 数据来源 | 真实 JSON | HTTP 响应 | 已知数据 + 伪造响应 |
| 依赖外部 | 否 | 是（需 skip） | 否（mock 隔离） |
| 关键技巧 | fixture 传数据 | 超时 + 三态 | monkeypatch + 已知答案 |

> 注意：D2 测的是"接口"，D3 用 mock 反而**不需要接口**了——这正是 mock 的价值：让测试脱离外部依赖，离线也绿。
