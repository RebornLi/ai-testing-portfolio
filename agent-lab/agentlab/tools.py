"""tools.py — Agent 工具集（确定性，可测试）。

每个工具 = 一个函数，带 name / description / parameters。
工具本身是纯函数，方便断言“调用是否被正确执行”。

认知边界：真实 Agent 的工具可能是联网、查数据库等副作用操作；
这里用纯函数替代，保证测试离线、可复现、可断言。
"""


def add(a: float, b: float) -> float:
    """加法工具：计算 a + b。"""
    return a + b


def multiply(a: float, b: float) -> float:
    """乘法工具：计算 a * b。"""
    return a * b


def lookup(city: str) -> str:
    """查天气工具：返回某城市天气（mock 返回确定值）。"""
    weather = {
        "beijing": "北京 晴 25°C",
        "shanghai": "上海 多云 28°C",
        "guangzhou": "广州 雨 30°C",
    }
    return weather.get(city.lower(), f"{city} 天气未知")


# 工具注册表：name -> (function, description, parameters)
TOOLS = {
    "add": {
        "function": add,
        "description": "计算两个数的和。",
        "parameters": {"a": "number", "b": "number"},
    },
    "multiply": {
        "function": multiply,
        "description": "计算两个数的积。",
        "parameters": {"a": "number", "b": "number"},
    },
    "lookup": {
        "function": lookup,
        "description": "查询某城市的天气。",
        "parameters": {"city": "string"},
    },
}


def tool_names():
    """返回所有可用工具名（用于 LLM 规划时参考）。"""
    return sorted(TOOLS.keys())


def invoke_tool(name: str, args: dict):
    """根据 name 调用对应工具，返回结果或抛未知工具错误。"""
    if name not in TOOLS:
        raise KeyError(f"未定义工具: {name}")
    func = TOOLS[name]["function"]
    return func(**args)
