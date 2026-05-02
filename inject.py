"""meowcat 注射器 — 绕过 wiring 校验，直接操作任何器官。

与 :meth:`signal` 和 :meth:`probe` 同为框架层的第三种通信方式。
只用于调试/管理/测试场景，生产环境可通过环境变量禁用。

安全设计：
- 不挂在 ``CatBase`` 上，必须显式 ``import`` + 构造
- 构造时打 ``warning`` 日志
- 生产环境可通过 ``MEOWCAT_DISABLE_NEEDLE=1`` 禁用

用法::

    from meowcat.inject import Needle

    needle = Needle(cat)
    await needle.poke(("brain", "hippocampus"), "add_entity", name="Python")
    await needle.poke_memory({"name": "fix", "content": "corrected"})
"""

from __future__ import annotations

import logging
import os
from typing import Any

from meowcat.wiring import Organ

logger = logging.getLogger("meowcat.needle")


class NeedleDisabledError(RuntimeError):
    """``MEOWCAT_DISABLE_NEEDLE=1`` 时构造 Needle 抛出。"""


class Needle:
    """注射器 — 绕过 wiring 校验，直接操作任何器官。

    安全设计：
    - 不挂在 CatBase 上，必须显式 import + 构造
    - 构造时报 warning 日志
    - 生产环境可通过 ``MEOWCAT_DISABLE_NEEDLE=1`` 禁用
    """

    def __init__(self, cat) -> None:
        """构造注射器。

        Args:
            cat: ``CatBase`` 或拥有 ``_host`` 属性的实例

        Raises:
            NeedleDisabledError: ``MEOWCAT_DISABLE_NEEDLE=1`` 时
        """
        if os.environ.get("MEOWCAT_DISABLE_NEEDLE") == "1":
            raise NeedleDisabledError(
                "Needle is disabled by MEOWCAT_DISABLE_NEEDLE=1"
            )
        self._cat = cat
        logger.warning(
            "Needle created — this bypasses wiring checks. "
            "For debugging/admin use only."
        )

    async def poke(self, to_organ: Organ, method: str, **kwargs: Any) -> Any:
        """直接调用目标器官的方法，不校验 wiring。

        Args:
            to_organ: 目标器官坐标，如 ``("brain", "hippocampus")``
            method: 方法名
            **kwargs: 方法参数

        Returns:
            方法返回值

        Raises:
            ValueError: 器官未 mount
            AttributeError: 方法不存在
        """
        import inspect

        target = self._cat._host.organ(*to_organ)
        if target is None:
            raise ValueError(f"Organ {to_organ} not mounted")
        fn = getattr(target, method, None)
        if fn is None:
            raise AttributeError(
                f"Organ {to_organ} has no method '{method}'"
            )
        result = fn(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result

    async def poke_memory(self, **entity_data: Any) -> Any:
        """快捷方法：直接写入海马体。

        Args:
            **entity_data: 传递给 ``add_entity()`` 的实体数据
        """
        return await self.poke(
            ("brain", "hippocampus"), "add_entity", **entity_data,
        )

    async def poke_focus(self, topic: str) -> Any:
        """快捷方法：直接更新额叶焦点。

        Args:
            topic: 焦点主题
        """
        return await self.poke(
            ("brain", "frontal"), "update_focus", result=topic,
        )

    async def poke_worldview(self, layer: str, key: str, value: Any) -> Any:
        """快捷方法：直接写入皮层世界观。

        Args:
            layer: 世界观层名（axioms/others/values/self）
            key: 键
            value: 值
        """
        return await self.poke(
            ("brain", "cortex"), "ingest",
            source="needle", layer=layer, key=key, value=value,
        )


__all__ = ["Needle", "NeedleDisabledError"]
