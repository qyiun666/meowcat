"""meowcat 预设通路 — 框架级的标准器官协作序列（v0.5.27 已废弃，保留向后兼容）。

v0.5.27 起所有静态方法内部委托给 ``cat.path_registry.run()``，
新代码请直接使用::

    from meowcat.path import Path
    result = await cat.path_registry.run("locate", query="hello")

本模块保持原有 API 签名不变，确保向后兼容。

.. deprecated:: v0.5.27
    请使用 :class:`meowcat.path.PathRegistry` 替代。
"""

from __future__ import annotations

import warnings
from typing import Any, Callable

# ⚠️ 以下 import 仅用于 build_conversation_pipeline 的类型参考
# 所有单步通路已迁移到 meowcat.path.BUILTIN_PATHS


_warned: bool = False


def _deprecated() -> None:
    global _warned
    if not _warned:
        warnings.warn(
            "Pathways is deprecated since v0.5.27. "
            "Use cat.path_registry.run() instead.",
            DeprecationWarning, stacklevel=3,
        )
        _warned = True


class Pathways:
    """[deprecated] 预设通路的命名空间。

    v0.5.27 起所有方法委托给 ``cat.path_registry.run()``。
    建议新代码直接使用 :class:`meowcat.path.PathRegistry`。
    """

    # ── 记忆回路 ──

    @staticmethod
    async def remember(cat, entity_data: dict[str, Any]) -> Any:
        """[deprecated] 记忆：存一条实体到海马体。

        委托给 ``cat.path_registry.run("remember", entity_data=entity_data)``。
        v0.5.26 起 from_organ 由 THALAMUS 修正为 BRAINSTEM（写权限约束）。

        Args:
            cat: ``CatBase`` 实例
            entity_data: 实体数据字典
        """
        _deprecated()
        return await cat.path_registry.run(
            cat, "remember", entity_data=entity_data,
        )

    @staticmethod
    async def locate(cat, query: str) -> Any:
        """[deprecated] 检索：从海马体查记忆。

        委托给 ``cat.path_registry.run("locate", query=query)``。

        Args:
            cat: ``CatBase`` 实例
            query: 检索查询
        """
        _deprecated()
        return await cat.path_registry.run(cat, "locate", query=query)

    # ── 推理回路 ──

    @staticmethod
    async def deep_reason(cat, prompt: str, context: str = "") -> str:
        """[deprecated] 深度推理：大脑 cerebrum 生成。

        委托给 ``cat.path_registry.run("deep_reason", prompt=prompt, context=context)``。

        Args:
            cat: ``CatBase`` 实例
            prompt: 推理提示词
            context: 上下文（如检索到的记忆）

        Returns:
            推理生成的文本
        """
        _deprecated()
        return await cat.path_registry.run(
            cat, "deep_reason", prompt=prompt, context=context,
        )

    @staticmethod
    async def fast_respond(cat, pattern: str) -> str:
        """[deprecated] 快速响应：小脑模式匹配。

        委托给 ``cat.path_registry.run("fast_match", pattern=pattern)``。
        v0.5.27 起 from_organ 由 THALAMUS 修正为 BRAINSTEM（布线约束）。

        Args:
            cat: ``CatBase`` 实例
            pattern: 匹配模式

        Returns:
            匹配到的响应文本
        """
        _deprecated()
        return await cat.path_registry.run(cat, "fast_match", pattern=pattern)

    # ── 输出回路 ──

    @staticmethod
    async def say(cat, text: str) -> Any:
        """[deprecated] 发言：经小脑协调后发声。

        委托给 ``cat.path_registry.run("say", text=text)``。

        Args:
            cat: ``CatBase`` 实例
            text: 要说的文本
        """
        _deprecated()
        return await cat.path_registry.run(cat, "say", text=text)

    # ── 完整对话流水线（闭包） ──

    @staticmethod
    def build_conversation_pipeline(
        cat,
    ) -> Callable[[str], Any]:
        """返回闭包：输入文本 → 检索记忆 → 推理 → 输出。

        这是最常用的合成通路。每个步骤都走 wiring 校验。

        Args:
            cat: ``CatBase`` 实例

        Returns:
            ``async def pipeline(user_input: str) -> str`` 闭包
        """
        _deprecated()

        async def pipeline(user_input: str) -> str:
            # 1. 检索记忆
            memory = await Pathways.locate(cat, user_input)
            context = str(memory) if memory else ""

            # 2. 推理
            reply = await Pathways.deep_reason(cat, user_input, context=context)

            # 3. 输出
            await Pathways.say(cat, reply)

            return reply

        return pipeline


__all__ = ["Pathways"]
