"""meowcat 器官职责声明表 — 一份不可改的器官作用说明。

每个器官登记其核心职责的一句话描述。本文件零业务逻辑，
只做声明，不改任何代码行为。增删器官时需同步更新本表。

本文件零第三方依赖，零 meowagent import。
"""

from __future__ import annotations

from typing import Final

from meowcat.anatomy import (
    AMYGDALA,
    ANOMALY_GROWTH,
    BRAINSTEM,
    CEREBELLUM,
    CEREBRUM,
    CORRECTION_GROWTH,
    CORTEX,
    CRYSTALLIZER,
    EARS,
    EYES,
    FRONTAL,
    HIPPOCAMPUS,
    HYPOTHALAMUS,
    MOUTH,
    PAWS,
    PURR,
    ROLE_EMERGENCE,
    TAIL,
    THALAMUS,
    WHISKERS,
)
from meowcat.wiring import Organ

ORGAN_ROLES: Final[dict[Organ, str]] = {
    # -- 脑区 --
    THALAMUS: "路由判断 — 所有输入先经过我，判向进大脑还是小脑",
    HIPPOCAMPUS: "记忆存取 — 记东西、找东西、忘东西的唯一入口",
    CEREBRUM: "深度推理 — 调用 LLM 做复杂思考",
    CEREBELLUM: "快速响应 — 模式匹配 + 所有效应器的唯一上游",
    AMYGDALA: "安全审查 — 危险检测 + 风险评估",
    FRONTAL: "焦点/计划 — 当前话题管理 + 任务分解",
    HYPOTHALAMUS: "自维护 — 记忆衰减 + 孤数据清理",
    CORTEX: "世界观 — 从经验中提炼认知、自我认知",
    BRAINSTEM: "协调中枢 — 生命周期 + 流程编排（不拥有数据）",
    # -- 感官 --
    EARS: "文本输入 — CLI/API/Discord/Telegram",
    EYES: "视觉输入 — 图像/视频",
    WHISKERS: "环境感知 — 浏览器 + 输入输出异常检测",
    PAWS: "工具执行 — Skill/MCP/命令的唯一执行入口",
    # -- 嗓音 --
    MOUTH: "语音输出 — TTS + 文本回复",
    PURR: "流式状态 — streaming 进度",
    TAIL: "状态栏 — CLI 状态信号",
    # -- 生长（v0.5.15 闭环 C）--
    ANOMALY_GROWTH: "异常沉淀 — 用户标记的异常模式写入持久化图",
    CORRECTION_GROWTH: "纠正固化 — 用户纠正的错误事实写入永久修正",
    CRYSTALLIZER: "经验结晶 — 累积多次使用后结晶为可复用技能",
    ROLE_EMERGENCE: "角色涌现 — 从交互中演化角色行为模式",
}

__all__ = ["ORGAN_ROLES"]
