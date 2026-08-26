# W1-D6 详细学习内容 · 代码质量 + README（6-8 小时版）

> 日期：2026-08-26（周三）｜ 目标：给项目做代码审查 + 写一份能让陌生人跑通的 README
> 验收：`jd-validator/README.md` 能让人 5 分钟跑通 + 全量 pytest 零失败零残留 + 学习日志 + commit

---

## ⏰ 今日时间块（6-8 小时）

| 时间段 | 时长 | 内容 |
|---|---|---|
| 09:00-10:30 | 1.5h | 代码质量：规范 + 注释 + 类型提示 + 命名 |
| 10:30-12:00 | 1.5h | 全量检查：找调试残留、死代码、隐患 |
| 14:00-16:00 | 2h | README 写作（项目介绍/安装/运行/测试/结果） |
| 16:00-17:30 | 1.5h | 实战：写 `jd-validator/README.md` |
| 19:00-20:00 | 1h | 代码审查 + 失败自测（先看失败长啥样） |
| 20:00-21:00 | 1h | 学习日志 + commit 打卡 |

---

## 一、代码质量规范（1.5h）★ 今日重点

> 好代码要"让陌生人能看懂"。从今天起，每个函数都过自检清单。

### 1.1 自检清单（每段代码写完都过一遍）
- [ ] 语法正确（能跑）
- [ ] 导入完整（不报错 No module named）
- [ ] 边界条件显式化（空列表、空字符串、None 会崩吗？）
- [ ] 异常有处理（别裸奔）
- [ ] 无调试残留（删掉 print 调试）

### 1.2 函数注释三件套
```python
def parse_salary(salary: str | None) -> tuple[int, int] | None:
    """薪资区间解析。

    参数：
        salary: 原始薪资字符串，如 "1.1-1.2万"
    返回：
        (最低, 最高) 元组；无法解析返回 None
    """
```

### 1.3 命名铁律
- 变量：`snake_case`（`job_count` 不是 `jobCount`）
- 常量：`UPPER_CASE`（`MAX_RETRY = 3`）
- 函数：动词开头（`parse_salary`）
- 类：`CamelCase`（`ReportBuilder`）

### 1.4 删调试残留
```bash
# 全项目搜残留，删干净
grep -rn "print(" jd-validator/src/   # 工具代码里的 print
grep -rn "pdb.set_trace()" .          # 断点残留
grep -rn "# TODO" .                   # 未完成标记
```

> ⚠️ **D6 检查发现**：`src/` 的函数在真实运行时会用真实路径。

---

## 二、全量检查（1.5h）

```bash
cd ~/ai-testing-portfolio/jd-validator
# 1. 全量测试
pytest
# 2. 搜死代码 / 调试残留
grep -rn "print(" src/ tests/
grep -rn "import sys" src/     # 看是否有冗余导入
```

### 常见隐患清单
| 隐患 | 怎么找 | 怎么办 |
|---|---|---|
| print 调试残留 | `grep print(` | 删掉 |
| 死代码 | 看 import 的库没用到 | 删 |
| 裸异常 | `try/except` 后只写 pass | 加日志 |
| 路径依赖 | 硬编码 `/Users/...` | 用 `os.path.dirname(__file__)` |

---

## 三、README 写作规范（2h）★ 重点

> 好 README = 陌生人照着做 5 分钟就能跑通。这是项目"门面"，招候选人会看。

### 3.1 README 结构
1. **项目标题 + 一句话介绍**
2. **功能特点**（这个项目能干嘛）
3. **环境要求**（Python 版本、依赖）
4. **安装步骤**（一步步复制即可）
5. **运行方式**（怎么跑测试 / 怎么用）
6. **测试结果**（截图或数据，证明跑过）
7. **项目结构**（目录说明）
8. **参考链接**

---

## 四、实战：写 jd-validator/README.md（1.5h）★ 今日产出①

创建 `jd-validator/README.md`：

````markdown
# jd-validator · JD 数据统计校验工具（W1）

> 定位：pytest 工程化作品集项目 —— 从零搭起一个可运行的完整 pytest 项目。

## 功能
- 解析 JD 薪资字符串（万/K/元/面议/日薪等格式）
- 统计 AI 岗位占比、城市分布、薪资档位、学历分布
- 参数化测试覆盖正常/边界/异常三态
- 数据驱动：用 61 条真实 JD 数据做验证

## 环境
- Python 3.12+
- pytest 8.x

## 安装
```bash
cd ~/ai-testing-portfolio/jd-validator
pip install pytest requests
```

## 运行
```bash
# 跑全部测试
pytest

# 看统计报告
python3 src/report.py
```

## 结构
```
src/     工具代码（salary_parser, jd_stats, report）
tests/   测试代码
data/    真实 JD 数据
```

## 结果（真实数据）
- 总岗位：61 条
- AI 相关占比：73.77%（45/61）
- 薪资可解析率：95.08%
- 城市 TOP1：西安（28 条）
````

### 3.2 关键提示
- 别写"安装依赖"这种废话 —— 写具体的 `pip install pytest requests`
- 代码块要有语言标记：bash 写 ```bash，python 写 ```python
- 结果要真实（别写"运行成功"，写"61 条数据全部校验通过"）

---

## 五、代码审查（1h）

> 检查清单：函数有无注释、命名是否规范、有无死代码。

### 审查模板（逐个 src/ 文件过）
| 检查项 | 状态 |
|---|---|
| 函数有无 docstring | 待查 |
| 变量命名 snake_case | 待查 |
| 有无 print 调试残留 | 待查 |
| 边界处理完整 | 待查 |
| 导入是否都用上 | 待查 |

---

## 六、失败自测（1h）★ 先看失败长啥样

> 检查 README 里的安装步骤是不是真的能跑通。

```bash
# 假装从零开始，验证 README 是否准确
cd /tmp
rm -rf jd-validator-test
git clone /home/mushan/ai-testing-portfolio/jd-validator jd-validator-test
# 或复制一份
cd jd-validator-test
pytest   # 能不能直接跑过？
```

> 关键：README 写"一行跑过"，实际 `pytest` 就必须真的一行绿。

---

## 七、学习日志模板（20:00）

复制 `~/ai-testing-portfolio/learning-log/2026-08-26.md`，填写：
- 今天学了什么：README 写作规范、代码审查清单
- 实测发现：仓库 README 有 TODO 占位，本周产出物清单都还没建
- 卡点：README 该怎么组织才算合格？
- 明日计划：D7 写里程碑 + 全部 push 到 GitHub

## 八、commit 打卡（21:00）

```bash
cd ~/ai-testing-portfolio
git add -A
git commit -m "W1D6: 写 jd-validator README + 代码审查 + README 模板"
git push
```

---

## 📌 今日自检清单

- [ ] 每个 src 函数有 docstring 注释
- [ ] 无 print 调试残留
- [ ] 无死代码
- [ ] 命名规范（snake_case）
- [ ] README 能让陌生人跑通
- [ ] 日志 + commit 完成

## 🆘 卡住怎么办

- `pytest` 报 ImportError → 检查 conftest.py 路径
- README 写"一行跑过"但实际报错 → 先修代码再改 README
- 卡 > 30min：看 README 优秀模板（GitHub 项目里找参考）
- 卡 > 2h：直接问我（木木），带报错信息

---

## 🎯 README 速记

```
标题 + 一句话
↓
功能特点
↓
环境 + 安装（复制即可）
↓
运行方式（跑测试/出报告）
↓
测试结果（真实数据）
↓
项目结构
```

> README 是项目门面，招候选人先看这个。
