"""tools.py — 被测系统：确定性工具集（离线、可复现）

被自动评测流水线使用，供 agent 调用。不依赖真实网络服务。
工具名 = 字典键；函数返回确定值。
"""

TOOLS = {
    "add": {
        "description": "两数相加",
        "function": lambda a, b: a + b,
    },
    "multiply": {
        "description": "两数相乘",
        "function": lambda a, b: a * b,
    },
    "lookup": {
        "description": "查询城市天气",
        "function": lambda city: {"beijing": "晴天", "shanghai": "多云"}.get(city, "未知"),
    },
}


def invoke_tool(name, args):
    """统一调用工具：按名分发，无此名抛 KeyError。"""
    if name not in TOOLS:
        raise KeyError(name)
    return TOOLS[name]["function"](**args)
