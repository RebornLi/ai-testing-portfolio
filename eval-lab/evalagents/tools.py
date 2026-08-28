"""eval_lab/tools.py — 确定性工具集（对齐 W6-D2/D3/D4）。

不依赖真实服务，全部可复现。被 agent.py / metrics.py 引用。
"""
# 可用工具集合
TOOLS = {"add", "lookup", "multiply", "weather"}

# 每个工具的模拟单价（元/次），用于 W6-D4 成本/延迟评测
PRICES = {"add": 0.001, "multiply": 0.001, "lookup": 0.002, "weather": 0.002}

# 查询库
_DB = {"beijing": "晴天", "atlantis": "未知"}


def invoke_tool(name, args):
    """执行一个工具调用，返回确定性结果。

    args 是字典，不同工具读取不同字段。
    未登记的工具抛出 ValueError。
    """
    if name == "add":
        return args["a"] + args["b"]
    if name == "multiply":
        return args["a"] * args["b"]
    if name == "lookup":
        return _DB.get(args.get("city", "未知"))
    if name == "weather":
        return "晴天 25°C"
    raise ValueError(f"未知工具：{name}")
