# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat keyword & prompt presets — bilingual base presets, user-customizable.

二语 可挂载:
  关键词预设 → 注入 Ears/Thalamus/Amygdala/Frontal
  提示词预设 → 注入 Brainstem/Cerebrum
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# =========================================================================
# KeywordPreset — 关键词预设 (挂载到 Ears/Thalamus/Amygdala/Frontal)
# =========================================================================

@dataclass
class KeywordPreset:
    """关键词预设 — language, domain, and safety keyword configuration.

    Mounted into: RenovatedEars, RenovatedThalamus, RenovatedAmygdala, RenovatedFrontal.
    Each organ picks the subset it needs (stop_words → Ears, commands → Thalamus, etc.)

    Attributes:
        name: Preset identifier, e.g. ``"zh_tech"``
        stop_words: Keywords to filter out during extraction
        command_patterns: ``{trigger_word: route}`` routing map
        danger_patterns: Compiled regex patterns for safety scanning
        topic_keywords: Domain-specific topic keywords by category
        priority_keywords: High-priority keywords that always match first
    """

    name: str = ""
    stop_words: frozenset[str] = field(default_factory=frozenset)
    command_patterns: dict[str, str] = field(default_factory=dict)
    danger_patterns: list[re.Pattern] = field(default_factory=list)
    topic_keywords: dict[str, list[str]] = field(default_factory=dict)
    priority_keywords: list[str] = field(default_factory=list)

    def merge(self, other: "KeywordPreset") -> "KeywordPreset":
        """Merge another preset into this one (other takes priority on conflict)."""
        return KeywordPreset(
            name=f"{self.name}+{other.name}",
            stop_words=self.stop_words | other.stop_words,
            command_patterns={**self.command_patterns,
                              **other.command_patterns},
            danger_patterns=self.danger_patterns + other.danger_patterns,
            topic_keywords={**self.topic_keywords, **other.topic_keywords},
            priority_keywords=self.priority_keywords + other.priority_keywords,
        )


# =========================================================================
# PromptPreset — 提示词预设 (挂载到 Brainstem/Cerebrum)
# =========================================================================

@dataclass
class PromptPreset:
    """提示词预设 — system prompt templates by route, project, or industry.

    Mounted into: RenovatedBrainstem, RenovatedCerebrum.

    Attributes:
        name: Preset identifier, e.g. ``"zh_medical"``
        templates: ``{route: prompt_template}`` — variables: {name}, {language}, {domain}
        fallback: Default template when no route match
        pre_prompt: Prepended before every system prompt (e.g. role, constraints)
        post_prompt: Appended after every system prompt (e.g. safety instructions)
    """

    name: str = ""
    templates: dict[str, str] = field(default_factory=dict)
    fallback: str = ""
    pre_prompt: str = ""
    post_prompt: str = ""

    def build(self, route: str, **variables: str) -> str:
        """Build a system prompt for the given route with variable substitution."""
        template = self.templates.get(route, self.fallback)
        if not template:
            template = "You are MeowCat, a helpful AI assistant."
        prompt = template
        for key, val in variables.items():
            prompt = prompt.replace(f"{{{key}}}", val)
        parts = []
        if self.pre_prompt:
            parts.append(self.pre_prompt)
        parts.append(prompt)
        if self.post_prompt:
            parts.append(self.post_prompt)
        return "\n".join(parts)

    def merge(self, other: "PromptPreset") -> "PromptPreset":
        """Merge another preset into this one (other takes priority on conflict)."""
        return PromptPreset(
            name=f"{self.name}+{other.name}",
            templates={**self.templates, **other.templates},
            fallback=other.fallback or self.fallback,
            pre_prompt=self.pre_prompt + "\n" +
            other.pre_prompt if other.pre_prompt else self.pre_prompt,
            post_prompt=self.post_prompt + "\n" +
            other.post_prompt if other.post_prompt else self.post_prompt,
        )


# =========================================================================
# OrganPrompt — per-organ 提示词插槽 (v1.3.6 挂载到 Cerebrum/Cerebellum)
# =========================================================================

@dataclass
class OrganPrompt:
    """Per-organ prompt slot — 每个 LLM 器官的提示词配置.

    v1.3.6: 框架层定义插槽形状。应用层填充内容。
    每个 LLM-bearing 器官（cerebrum/cerebellum）挂一个 OrganPrompt 实例。

    Attributes:
        identity: 身份描述，这个器官是谁、承担什么角色.
            e.g. ``"你是 {name} 的大脑皮层，负责深度推理和决策。"``
        perspective: 视角声明，这个器官以什么视角看世界.
            e.g. ``"你可以访问所有工具和记忆。"``
        output_format: 输出格式约束，期望的输出结构.
            e.g. ``"<thinking>...</thinking>\\n<response>...</response>"``
        route_templates: per-route 模板覆盖（可选），覆盖 PromptPreset 的路由模板.
            e.g. ``{"chat": "...", "tool": "..."}``
    """

    identity: str = ""
    perspective: str = ""
    output_format: str = ""
    route_templates: dict[str, str] = field(default_factory=dict)


# =========================================================================
# ══════════════════  Bilingual Presets  二语预设 ═══════════════════════
# =========================================================================


# -- English stop words (common function words) ---------------------

_EN_STOP: frozenset[str] = frozenset({
    "the", "is", "a", "an", "in", "on", "at", "to", "for", "of", "and",
    "or", "it", "be", "was", "are", "this", "that", "with", "from", "by",
    "as", "but", "not", "so", "if", "we", "you", "i", "he", "she", "they",
    "me", "my", "your", "his", "her", "our", "do", "does", "did", "can",
    "will", "would", "could", "should", "has", "have", "had", "been",
    "just", "very", "really", "about", "all", "no", "yes", "what", "when",
    "where", "which", "who", "how", "why",
})

# -- Chinese stop words (常用停用词) ---------------------------------

_ZH_STOP: frozenset[str] = frozenset({
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
    "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "些",
    "吗", "吧", "啊", "呢", "哦", "嗯", "哈", "呀", "嘛", "呗",
    "可以", "需要", "应该", "能够", "可能", "已经", "还是", "但是",
    "因为", "所以", "如果", "虽然", "不过", "然后", "之后", "之前",
    "什么", "怎么", "怎么样", "为什么", "哪里", "哪个", "多少",
    "这个", "那个", "这些", "那些", "这样", "那样", "这里", "那里",
    "只是", "就是", "还是", "不是", "还有", "没有",
    "让", "把", "被", "给", "对", "从", "向", "用", "以",
    "每", "最", "更", "只", "才", "都", "再", "又", "也",
    "请", "帮", "麻烦", "谢谢", "请问",
})

# -- English command patterns ---------------------------------------

_EN_COMMANDS: dict[str, str] = {
    "help": "chat", "info": "chat", "status": "chat",
    "tool": "tool", "tools": "tool",
    "run": "action", "exec": "action", "execute": "action",
    "file": "file", "read": "file", "write": "file", "edit": "file",
    "memory": "memory", "remember": "memory", "forget": "memory", "recall": "memory",
    "maintenance": "maintenance", "cleanup": "maintenance",
    "diagnose": "diagnostic", "health": "diagnostic", "check": "diagnostic",
    "search": "memory", "find": "memory", "lookup": "memory",
    "create": "file", "delete": "action", "remove": "action",
    "web": "action", "fetch": "action", "download": "action",
    "config": "chat", "settings": "chat", "setup": "chat",
}

# -- Chinese command patterns (中文指令路由) --------------------------

_ZH_COMMANDS: dict[str, str] = {
    "帮助": "chat", "帮忙": "chat", "说明": "chat", "指南": "chat",
    "工具": "tool", "执行": "action", "运行": "action",
    "文件": "file", "读取": "file", "写入": "file", "编辑": "file",
    "记忆": "memory", "记住": "memory", "忘记": "memory", "回想": "memory",
    "维护": "maintenance", "清理": "maintenance",
    "诊断": "diagnostic", "检查": "diagnostic", "健康": "diagnostic",
    "搜索": "memory", "查找": "memory", "寻找": "memory",
    "创建": "file", "删除": "action", "移除": "action",
    "网络": "action", "获取": "action", "下载": "action",
    "配置": "chat", "设置": "chat", "安装": "chat",
    "你好": "chat", "嗨": "chat", "聊天": "chat",
    "分析": "chat", "解释": "chat", "总结": "chat", "翻译": "chat",
    "写": "file", "代码": "file", "脚本": "file", "测试": "chat",
    "安全": "diagnostic", "风险": "diagnostic", "扫描": "diagnostic",
}

# -- English danger patterns (SQL/XSS/shell/path) -------------------

_EN_DANGER: list[re.Pattern] = [
    re.compile(
        r"(?i)(?:drop\s+table|delete\s+from|truncate\s+table|alter\s+table)\b"),
    re.compile(r"(?i)(?:exec\s*\(|eval\s*\(|__import__\s*\(|subprocess\b)"),
    re.compile(r"(?i)(?:rm\s+-rf\s+/|:\(\)\s*\{\s*:\|:&\s*\}|wget\s+.*\|sh)"),
    re.compile(r"(?i)<script\b.*?>"),
    re.compile(r"(?i)(?:sudo\b|chmod\s+777|chown\s+root)"),
    re.compile(r"(?i)(?:/etc/(?:passwd|shadow)|\.\./\.\./)"),
    re.compile(r"(?i)(?:union\s+select|or\s+1=1|'\s+or\s+'1'='1)"),
    re.compile(r"(?i)(?:cmd\.exe|powershell\b|/bin/bash)"),
]

# -- Chinese danger patterns (中文安全风险) --------------------------

_ZH_DANGER: list[re.Pattern] = [
    re.compile(r"(?i)(?:drop\s+table|delete\s+from|truncate\s+table)\b"),
    re.compile(r"(?i)(?:exec\s*\(|eval\s*\(|__import__\s*\()"),
    re.compile(r"删除数据库|清空表|篡改记录|非法访问"),
    re.compile(r"系统命令|执行脚本|反弹shell|提权"),
    re.compile(r"窃取|泄露|破解|越权|绕过验证"),
    re.compile(r"社工|钓鱼|欺诈|虚假"),
    re.compile(r"(?i)(?:/etc/(?:passwd|shadow)|\.\./\.\./)"),
    re.compile(r"(?i)(?:rm\s+-rf\s+|sudo\b|chmod\s+777)"),
    re.compile(r"(?i)malicious|exploit|injection|xss|csrf|backdoor"),
]


# =========================================================================
# ════════════════  Built-in Keyword Presets  ═══════════════════════
# =========================================================================

KW_EN: KeywordPreset = KeywordPreset(
    name="en",
    stop_words=_EN_STOP,
    command_patterns=_EN_COMMANDS,
    danger_patterns=list(_EN_DANGER),
    priority_keywords=["help", "search", "run", "create", "delete", "config"],
)

KW_ZH: KeywordPreset = KeywordPreset(
    name="zh",
    stop_words=_ZH_STOP,
    command_patterns=_ZH_COMMANDS,
    danger_patterns=list(_ZH_DANGER),
    priority_keywords=["帮助", "搜索", "查找", "分析", "执行", "创建", "删除"],
)

KW_BILINGUAL: KeywordPreset = KW_EN.merge(KW_ZH)


# =========================================================================
# ════════════════  Built-in Prompt Presets  ═══════════════════════
# =========================================================================

PROMPT_DEFAULT: PromptPreset = PromptPreset(
    name="default",
    templates={
        "chat": "You are {name}, a helpful AI assistant. Current domain: {domain}. Respond in {language}.",
        "tool": "You are {name}. Execute tools carefully. Check security before running.",
        "action": "You are {name}. Perform the requested action. Report results clearly.",
        "file": "You are {name}. Handle file operations safely. Never write to system paths.",
        "memory": "You are {name}. Search and retrieve relevant memories for the user.",
        "maintenance": "You are {name}. Perform system maintenance tasks.",
        "diagnostic": "You are {name}. Run diagnostic checks and report health status.",
    },
    fallback="You are {name}, a helpful AI assistant. Current domain: {domain}. Respond in {language}.",
    pre_prompt="",
    post_prompt="Be concise, accurate, and helpful. Do not fabricate information.",
)

PROMPT_ZH: PromptPreset = PromptPreset(
    name="zh",
    templates={
        "chat": "你是{name}，一个智能助手。当前领域：{domain}。用{language}回答。",
        "tool": "你是{name}。谨慎执行工具，执行前检查安全性。",
        "action": "你是{name}。执行请求的操作，清晰报告结果。",
        "file": "你是{name}。安全处理文件操作，不写入系统路径。",
        "memory": "你是{name}。为用户搜索和检索相关记忆。",
        "maintenance": "你是{name}。执行系统维护任务。",
        "diagnostic": "你是{name}。运行诊断检查，报告健康状态。",
    },
    fallback="你是{name}，一个智能助手。当前领域：{domain}。用{language}回答。",
    pre_prompt="",
    post_prompt="请简洁、准确、有帮助地回答。不要编造信息。",
)


# =========================================================================
# ══════════════  Preset Registry (可挂载查找表) ════════════════════
# =========================================================================

# Keyword presets
KW_PRESETS: dict[str, KeywordPreset] = {
    "en": KW_EN,
    "zh": KW_ZH,
    "bilingual": KW_BILINGUAL,
}

# Prompt presets
PROMPT_PRESETS: dict[str, PromptPreset] = {
    "default": PROMPT_DEFAULT,
    "zh": PROMPT_ZH,
}


__all__ = [
    "KeywordPreset", "PromptPreset", "OrganPrompt",
    "KW_EN", "KW_ZH", "KW_BILINGUAL",
    "PROMPT_DEFAULT", "PROMPT_ZH",
    "KW_PRESETS", "PROMPT_PRESETS",
]
