# W1-D1 详细学习内容 · pytest 基础（6-8 小时版）

> 日期：2026-08-21（周五）｜ 目标：pytest 从零到能写数据校验测试
> 验收：JD 数据校验 5 用例全绿 + 学习日志 + commit

---

## ⏰ 今日时间块（6-8 小时）

| 时间段 | 时长 | 内容 |
|---|---|---|
| 09:00-10:30 | 1.5h | 环境准备 + 第一个 pytest 测试 |
| 10:30-12:00 | 1.5h | 断言体系详解（核心中的核心） |
| 14:00-15:30 | 1.5h | fixture 入门 + conftest |
| 15:30-17:00 | 1.5h | 运行方式 + 选择测试 + 配置 |
| 19:00-20:30 | 1.5h | 实战：JD 数据校验 5 用例 |
| 20:30-21:00 | 0.5h | 学习日志 + commit 打卡 |

---

## 一、环境准备（1.5h）

### 1.1 检查 Python 环境
```bash
python3 -V        # 应为 Python 3.12.x
pip3 --version    # 确认 pip 可用
```

### 1.2 创建虚拟环境（重要！项目隔离，不污染系统）
```bash
cd ~/ai-testing-portfolio
mkdir -p jd-validator && cd jd-validator
python3 -m venv .venv
source .venv/bin/activate        # 激活（每次开终端都要执行）
# 终端提示符前面出现 (.venv) 即成功
```

### 1.3 安装 pytest + requests
```bash
pip install pytest requests
pytest --version   # 看到 pytest 8.x 即成功
```

### 1.4 准备测试数据
```bash
cp ~/桌面/AI测试岗位JD数据-61条.json ~/ai-testing-portfolio/jd-validator/data.json
```
（JSON 文件是 61 条 JD 数据，今天所有练习都围绕它）

---

## 二、第一个 pytest 测试（30min）

### 2.1 测试文件命名铁律
- 文件名：`test_xxx.py` 或 `xxx_test.py`（pytest 默认只认这两种）
- 测试函数：`def test_xxx():` 开头
- 放哪个目录都行，pytest 自动递归发现

### 2.2 写第一个测试
```bash
mkdir tests
```
创建 `tests/test_first.py`：
```python
"""第一个测试：体验 pytest 工作流"""

def test_hello():
    assert 1 + 1 == 2

def test_string():
    name = "reborn"
    assert name == "reborn"
    assert len(name) == 6
    assert "eb" in name

def test_fail_demo():
    # 故意失败看效果（学会读失败信息），看完删掉
    assert 1 == 2
```

### 2.3 运行
```bash
pytest                 # 运行所有测试
pytest -v              # 详细模式，显示每个用例
pytest -v tests/test_first.py   # 只跑这个文件
```
**必看输出**：`PASSED/FAILED`、失败时的 `assert 1 == 2` 位置、`F 表示失败`、`E 表示错误`（失败=断言没过，错误=代码异常，两者区别要记住）

⚠️ 运行前先删掉 `test_fail_demo`，保持全绿

---

## 三、断言体系详解（1.5h）★ 今日重点

> 测试的核心 = 断言。pytest 的 `assert` 比 unittest 简洁 10 倍

### 3.1 基础断言（直接 assert + 表达式）
```python
def test_basic_asserts():
    # 数值
    assert 3 > 2
    assert 10 == 10
    # 字符串
    assert "hello" == "hello"
    assert "AI" in "AI测试工程师"
    assert "abc".startswith("a")
    # 列表/字典
    assert [1, 2, 3] == [1, 2, 3]
    assert "python" in ["python", "java", "go"]
    assert {"name": "reborn"}["name"] == "reborn"
    assert "salary" in {"salary": "1-2万"}
    # 布尔
    assert True
    assert not False
```

### 3.2 浮点比较（重点！AI 场景经常算指标）
```python
def test_float_compare():
    # ❌ 错误：assert 0.1 + 0.2 == 0.3  （浮点精度问题会失败）
    # ✅ 正确：用 pytest.approx
    assert 0.1 + 0.2 == pytest.approx(0.3)
    # 指定精度
    assert 1.23456 == pytest.approx(1.234, abs=0.001)   # 绝对误差
    assert 100.5 == pytest.approx(100, rel=0.01)         # 相对误差 1%
```

### 3.3 异常断言（pytest.raises）——测"应该报错"的场景
```python
import pytest

def divide(a, b):
    if b == 0:
        raise ValueError("除数不能为0")
    return a / b

def test_divide_normal():
    assert divide(10, 2) == 5

def test_divide_by_zero():
    with pytest.raises(ValueError):
        divide(10, 0)

def test_divide_by_zero_check_message():
    # 进阶：同时校验异常信息
    with pytest.raises(ValueError, match="除数"):
        divide(10, 0)
```

### 3.4 集合/序列断言技巧（数据分析常用）
```python
def test_collection_asserts():
    data = [1, 2, 3, 4, 5]
    assert len(data) == 5
    assert max(data) == 5
    assert min(data) == 1
    assert sum(data) == 15
    assert all(x > 0 for x in data)       # 全部 > 0
    assert any(x == 3 for x in data)      # 存在 3
    assert set(data) == {1, 2, 3, 4, 5}   # 去重后相等
```

### 3.5 断言失败信息（必学调试技巧）
```python
def test_fail_message():
    # 第三个参数是失败时显示的自定义信息
    assert 1 == 2, "1 应该等于 2，但失败了——写清楚原因，失败时快速定位"
```
跑一下看输出，失败信息里会显示你的自定义文案。

**练习**：自己写 3 个"会失败"的测试，观察失败输出长什么样（然后改对）。失败信息是你以后调试的老朋友，要熟悉。

---

## 四、fixture 入门 + conftest（1.5h）

> fixture = 测试的"前置准备"和"后置清理"，复用代码

### 4.1 最简单的 fixture
```python
import pytest

@pytest.fixture
def jd_data():
    """加载 JD 数据（今天所有测试都靠它）"""
    import json
    with open("data.json", encoding="utf-8") as f:
        return json.load(f)

def test_jd_count(jd_data):
    assert len(jd_data) == 61

def test_jd_has_position(jd_data):
    for job in jd_data:
        assert job["职位"], "每条必须有职位名"
```

### 4.2 fixture 的 yield 形式（setup/teardown）
```python
@pytest.fixture
def temp_db():
    """setup: 创建临时资源；teardown: 自动清理"""
    import tempfile, os
    path = tempfile.mktemp(suffix=".db")
    yield path          # 测试在这里执行
    os.remove(path)     # 测试结束后自动清理
```

### 4.3 fixture 作用域（性能优化关键）
```python
@pytest.fixture(scope="session")
def jd_data():
    """session 级：整个测试会话只加载一次（61条数据加载很快，但大文件时关键）"""
    import json
    with open("data.json", encoding="utf-8") as f:
        return json.load(f)
# scope 可选：function(默认,每个用例一次)/class/module/session(整个会话一次)
```

### 4.4 conftest.py（共享 fixture 的魔法文件）
- 在 `tests/` 目录下创建 `conftest.py`，把 `jd_data` fixture 放进去
- 该目录下所有测试文件自动可用，无需 import

```python
# tests/conftest.py
import json
import pytest

@pytest.fixture(scope="session")
def jd_data():
    with open("data.json", encoding="utf-8") as f:
        return json.load(f)
```

---

## 五、运行方式 + 选择测试 + 配置（1.5h）

### 5.1 常用运行参数（背下来）
```bash
pytest                      # 全量
pytest -v                   # 详细（显示每个用例名）
pytest -q                   # 安静模式
pytest -k "jd"              # 只跑名字含 jd 的用例
pytest -k "salary or count" # 名字含 salary 或 count
pytest -x                   # 遇到第一个失败就停（调试用）
pytest --maxfail=2          # 失败 2 个就停
pytest -s                   # 显示 print 输出（默认隐藏）
pytest --collect-only       # 只列出所有用例，不执行（检查发现规则）
pytest -m "slow"            # 按标记运行（下面配置）
```

### 5.2 pytest.ini 配置（项目根目录创建）
```ini
# jd-validator/pytest.ini
[pytest]
testpaths = tests          # 只搜 tests 目录
addopts = -v --tb=short    # 默认详细模式 + 短回溯（失败信息更清爽）
markers =
    slow: 运行较慢的测试
    api: 依赖本地服务的测试
```

### 5.3 标记（marker）——分类管理测试
```python
import pytest

@pytest.mark.api          # 标记为 API 测试（D2 用）
def test_health():
    ...

@pytest.mark.slow
def test_big_analysis():
    ...
```
运行：`pytest -m api`（只跑 API 类）、`pytest -m "not api"`（排除）

---

## 六、实战：JD 数据校验 5 用例（1.5h）★ 今日产出

创建 `tests/test_jd_data.py`（用 conftest 里的 fixture）：

```python
"""61 条 JD 数据校验测试（W1-D1 实战产出）"""
import pytest

# 已知城市列表（从数据里提取的 17 城）
KNOWN_CITIES = {"西安","深圳","北京","上海","南京","杭州","成都","广州","武汉","郑州","长春","哈尔滨","南宁","济南","重庆","常州","烟台"}

def test_total_count(jd_data):
    """① 总数 = 61"""
    assert len(jd_data) == 61

def test_all_have_position(jd_data):
    """② 每条都有非空职位名"""
    for job in jd_data:
        assert job.get("职位"), f"缺失职位名: {job}"

def test_all_have_valid_salary(jd_data):
    """③ 薪资字段合法：包含数字 或 为面议"""
    for job in jd_data:
        salary = job.get("薪资", "")
        assert "面议" in salary or any(c.isdigit() for c in salary), f"薪资异常: {salary}"

def test_ai_ratio_over_60(jd_data):
    """④ AI 相关占比 ≥ 60%（求职核心指标）"""
    ai_count = sum(1 for j in jd_data if j.get("相关度") == "AI相关")
    ratio = ai_count / len(jd_data)
    assert ratio >= 0.6, f"AI 相关占比 {ratio:.1%} < 60%"

def test_city_in_known_list(jd_data):
    """⑤ 城市都在已知列表"""
    for job in jd_data:
        city = job.get("城市", "西安")
        assert city in KNOWN_CITIES, f"未知城市: {city}"

def test_no_duplicates(jd_data):
    """⑥ 无重复（职位+公司+薪资 唯一）"""
    keys = [(j["职位"], j["公司"], j["薪资"]) for j in jd_data]
    assert len(keys) == len(set(keys)), "存在重复条目"
```

### 运行 & 验证
```bash
pytest tests/test_jd_data.py -v
# 期望：6 个用例全部 PASSED
```

### 若失败（自己先修再问）
- 失败 → 读失败信息 → 判断是"数据问题"还是"断言写错" → 修正
- 这是今天最重要的练习：**学会读失败信息**

---

## 七、今日学习日志模板（20:30）

复制 `~/ai-testing-portfolio/learning-log/2026-08-21.md`（模板已建好），填写：
- 今日目标完成度（打勾）
- 学到什么：pytest 断言体系、fixture、参数化概念
- 疑问/卡点：如"fixture 和普通函数有啥区别？""为什么用 venv？"
- 明日计划：D2 requests 接口测试（预习 requests 文档）

## 八、commit 打卡（21:00）

```bash
cd ~/ai-testing-portfolio
git add -A
git commit -m "W1D1: pytest 基础 + JD 数据校验测试 6 用例"
git push
```

---

## 📌 今日自检清单

- [ ] venv 虚拟环境建好并激活
- [ ] pytest 安装，`pytest --version` 成功
- [ ] 断言 5 类全会（基础/浮点/异常/集合/自定义信息）
- [ ] fixture 会用（普通 + yield + scope + conftest）
- [ ] 6 个 JD 校验用例全绿
- [ ] 学习日志已写
- [ ] commit + push 成功

## 🆘 卡住怎么办

- 卡 > 30min：先看 pytest 官方文档 https://docs.pytest.org（中文教程搜"pytest 入门"）
- 卡 > 2h：直接问我（木木），带上报错信息
- 服务没起来（D2 才用）：今天不涉及
