"""meowcat 器官容器 — OrganHost 纯容器子系统（v0.5.9 抽离）。

职责仅一件：**存/取器官**。零依赖（不需要 wiring/events/reflex），
可单独实例化给只想要"器官注册表"的极简场景使用::

    host = OrganHost("toy")
    host.mount("brain", "cerebrum", my_brain, protocol=LLMBrainProtocol)
    brain = host.organ("brain", "cerebrum")

Nervous / CatBase 都通过显式依赖注入持有 OrganHost 实例，
不再让容器状态散落在多个类里。

P-02 哲学：最少代码量。OrganHost 不做事件、不做 wiring、不做 protocol
查找——那些是 Nervous / assembly 的职责。
"""

from __future__ import annotations

from typing import Any

from meowcat.errors import OrganNotMountedError, OrganProtocolMismatchError


class OrganHost:
    """器官容器——mount / organ / has / unmount 的纯数据结构。"""

    def __init__(self, cat_id: str) -> None:
        self.cat_id = cat_id
        self._organs: dict[str, dict[str, Any]] = {}

    # -- 写接口 ------------------------------------------------------

    def mount(
        self,
        category: str,
        name: str,
        organ: Any,
        *,
        protocol: type | None = None,
    ) -> None:
        """挂载一个器官。

        Args:
            category: 器官分类（``brain`` / ``sense`` / ``voice`` / ``storage`` 等）
            name: 器官名（``hippocampus`` / ``ears`` / ``tail`` 等）
            organ: 具体实现实例
            protocol: 可选 ``@runtime_checkable`` Protocol 类，
                非 None 时 ``isinstance(organ, protocol)`` 校验，
                不匹配抛 :class:`OrganProtocolMismatchError`。
        """
        if protocol is not None and not isinstance(organ, protocol):
            raise OrganProtocolMismatchError(
                category, name, protocol, organ,
            )
        self._organs.setdefault(category, {})[name] = organ

    def unmount(self, category: str, name: str) -> bool:
        """卸载一个器官，不存在返回 False。"""
        bucket = self._organs.get(category)
        if bucket is None or name not in bucket:
            return False
        del bucket[name]
        return True

    # -- 读接口 ------------------------------------------------------

    def organ(self, category: str, name: str) -> Any:
        """取出一个已挂载的器官。未挂载抛 :class:`OrganNotMountedError`。"""
        bucket = self._organs.get(category)
        if bucket is None or name not in bucket:
            raise OrganNotMountedError(category, name)
        return bucket[name]

    def organs(self, category: str) -> dict[str, Any]:
        """返回某个分类下所有器官的快照（只读拷贝）。"""
        return dict(self._organs.get(category, {}))

    def has_organ(self, category: str, name: str) -> bool:
        """检查器官是否已挂载。"""
        return name in self._organs.get(category, {})

    def list_all_organs(self) -> list[tuple[str, str]]:
        """返回所有已挂载器官的坐标列表 ``[(category, name), ...]``。

        v0.5.14: 供 /healthz 听诊器遍历所有器官。
        """
        result: list[tuple[str, str]] = []
        for category, bucket in sorted(self._organs.items()):
            for name in sorted(bucket.keys()):
                result.append((category, name))
        return result

    def assert_organs_mounted(
        self, required: list[tuple[str, str]],
    ) -> None:
        """断言必需器官已挂载，否则抛 :class:`OrganNotMountedError`。

        用于应用层在装配完成后校验解剖完整性。
        具体"主猫必须有哪些器官"由应用层决定，OrganHost 只提供校验机制。

        Args:
            required: ``[(category, name), ...]`` 必需器官清单
        """
        for category, name in required:
            if not self.has_organ(category, name):
                raise OrganNotMountedError(category, name)


__all__ = ["OrganHost"]
