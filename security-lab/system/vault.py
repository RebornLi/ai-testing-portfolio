"""vault.py — W8 安全测试被测系统：带权限的机密保险库 + prompt injection 攻击面。

这是一个"会中漏洞"的确定性系统，专门用来练安全测试功夫：
  - 权限边界：用户角色不该拿到管理员机密
  - prompt injection：攻击者注入指令不该被执行
  - 信息泄露：攻击者绕弯（base64/逐字）不该拿到机密

系统分两个版本：
  - InsecureAgent：默认实现，**存在漏洞**（会被注入、越权拿到机密）——安全测试会抓住它。
  - SecureAgent：修复后的实现（拒绝注入 + 强制权限）——安全测试应通过。

全部离线、可复现，不依赖真实模型。
"""
import re
import base64


class SecretVault:
    """带权限的机密保险库。每个机密有 min_role 最低角色要求。"""

    ROLE_RANK = {"user": 1, "admin": 2, "root": 3}

    def __init__(self):
        self.secrets = {
            "api_token": {"value": "TOKEN-SECRET-8899", "min_role": "user"},
            "admin_key": {"value": "ADMIN-KEY-1234", "min_role": "admin"},
            "db_password": {"value": "DB-PASS-5678", "min_role": "admin"},
        }

    def has_secret(self, name):
        return name in self.secrets

    def get_secret(self, role, name):
        """按角色返回机密；权限不足抛 PermissionError。"""
        if name not in self.secrets:
            raise KeyError(name)
        want = self.ROLE_RANK[self.secrets[name]["min_role"]]
        have = self.ROLE_RANK.get(role, 0)
        if have < want:
            raise PermissionError(f"角色 {role} 无权访问机密 {name}")
        return self.secrets[name]["value"]


class PromptInjectionGuard:
    """检测 prompt injection 指令注入攻击。

    攻击特征：要求 agent"忽略之前的指令 / 改行做事 / 透露机密"。
    detect() 返回 (is_attack, reason)。
    """

    ATTACK_MARKERS = [
        r"(?i)ignore\s+(the\s+)?(previous\s+)?(system\s+)?(instructions|prompt|rules)",
        r"(?i)disregard\s+(...|this)?",
        r"(?i)(instead|do\s+this\s+instead|now\s+do)",
        r"(?i)you\s+are\s+(now|acting\s+as)",
        r"(?i)secret\s+command",
        r"(?i)sys\.command",
        r"(?i)root\s+access",
        r"(?i)reveal(?:s|ed)?\s+(?:the\s+)?(secret|key|password|token)",
        r"(?i)泄露(?:...|这个|上述)?.*(?:机密|密钥|密码|token)",
    ]

    def __init__(self):
        self.patterns = [re.compile(p) for p in self.ATTACK_MARKERS]

    def detect(self, prompt):
        for p in self.patterns:
            m = p.search(prompt)
            if m:
                # ★ Match 没有 .pattern 属性；用编译后的 p.pattern 取规则原文
                return True, p.pattern
        return False, ""


class InsecureAgent:
    """存在漏洞的 agent（v1，默认实现）。

    漏洞点：
      1. 不检测 prompt injection——攻击者注入"泄露机密"指令它照做。
      2. 调用 get_secret 时不强制角色权限，越权也能拿。
    安全测试会抓住这两处。"""

    def __init__(self, role="user"):
        self.role = role
        self.vault = SecretVault()
        self.guard = PromptInjectionGuard()

    def process(self, prompt, context=""):
        # 漏洞1：prompt injection 零防护 —— 用户说的任何"机密"都当真实指令执行
        # 漏洞2：直接读保险库字典，完全绕过角色权限检查
        m = re.search(r"(api_token|admin_key|db_password)", prompt, re.IGNORECASE)
        if m:
            name = m.group(1)
            if self.vault.has_secret(name):
                value = self.vault.secrets[name]["value"]  # 绕过 get_secret 的权限检查
                return {"answer": value, "attack": False,
                        "injected": True, "leaked": True}
        return {"answer": "抱歉，我只能回答与工作相关的问题。",
                "attack": False, "injected": False, "leaked": False}


class SecureAgent:
    """修复后的安全 agent。

    修复点：
      1. prompt injection 防护：检测到注入指令 → 拒绝执行，只回应合法上下文。
      2. 强制权限：get_secret 角色不足 → 拒绝，绝不返回机密。
      3. 输出脱敏：即便意外持有机密，也不原样输出（防绕弯泄露）。
    """

    def __init__(self, role="user"):
        self.role = role
        self.vault = SecretVault()
        self.guard = PromptInjectionGuard()

    def process(self, prompt, context=""):
        # 修复1：检测并拒绝注入攻击
        is_attack, _ = self.guard.detect(prompt)
        if is_attack:
            return {"answer": "检测到异常指令，已拒绝执行该请求。",
                    "attack": True, "injected": False, "refused": True}

        # 合法路径：只处理上下文里的正常查询
        m = re.search(r"(?:查询|显示|给我)[\s:：]*(\w+)", prompt)
        if m and self.vault.has_secret(m.group(1)):
            # 修复2：强制角色权限，越权一律拒绝
            try:
                return {"answer": self.vault.get_secret(self.role, m.group(1)),
                        "attack": False, "injected": False, "refused": False}
            except PermissionError as e:
                return {"answer": f"权限不足：{e}", "attack": False,
                        "injected": False, "refused": True}
        return {"answer": "抱歉，我只能回答与工作相关的问题。",
                "attack": False, "injected": False, "refused": False}
