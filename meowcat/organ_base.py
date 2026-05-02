"""meowcat 器官便捷基类 — OrganMixin（v0.5.11 新增）。

**定位**：可选继承的 mixin，给器官提供零栈帧开销的 signal/probe 快捷方法。

**背景**：v0.5.0~v0.5.10 以来，跨器官调用必须走
``await self.cat.signal(FROM_ORGAN, TO_ORGAN, method, ...)``，写法长且每次
都要显式传 from_organ，容易手滑写错（如 ``BRAINSTEM`` 写成 ``CEREBRUM``）。

v0.5.11 通过 ``OrganMixin`` 让器官在构造时一次性绑定 ``self._self_coord``
和 ``cat`` 弱引用，之后写 ``await self._signal_to(TO, method, ...)`` 即可，
框架自动补上 from_organ——从调用点消除人工拼错空间。

**与 cat.ask() 方案的对比**：原 plan 提过 ``cat.ask(to, method)`` 用
``inspect`` 栈帧推断 from_organ，但 inspect 开销通常 2-5μs，与 signal 热路径
``<5μs`` 目标冲突。``OrganMixin`` 用构造时绑 ``_self_coord`` 的方式彻底回避
栈帧反射，保持 signal 热路径原速。

**向后兼容**：完全可选。现有器官不继承 ``OrganMixin`` 继续显式写
``self.cat.signal(...)`` 也正常工作。

**典型用法**::

    from meowcat import OrganMixin
    from meowcat.biology import BRAINSTEM, CORTEX
    from meowcat.protocols import CatProtocol

    class BrainStem(OrganMixin):
        name = "brainstem"

        def __init__(self, cat: CatProtocol) -> None:
            OrganMixin.__init__(self, cat, BRAINSTEM)
            # 业务构造...

        async def some_flow(self) -> None:
            # 旧写法：await self.cat.signal(BRAINSTEM, CORTEX, "synthesize", max_tokens=200)
            # 新写法：
            wv = await self._signal_to(CORTEX, "synthesize", max_tokens=200)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from meowcat.protocols import CatProtocol
    from meowcat.wiring import Organ


class OrganMixin:
    """器官便捷基类：构造时绑定 ``(cat, self_coord)``，提供零栈帧开销的
    ``_signal_to`` / ``_probe`` 快捷方法。

    **本类不持有业务状态**，只持有 ``_cat_ref`` 和 ``_self_coord``——两个指针。
    具体器官业务逻辑由子类负责。

    ``__slots__`` 声明避免每个器官实例为这两个字段额外分配 ``__dict__``
    条目；若子类已使用 ``__dict__``（无 ``__slots__``），mixin 的 slots
    叠加仍然有效，只是不产生内存节省。
    """

    __slots__ = ("_cat_ref", "_self_coord")

    def __init__(self, cat: CatProtocol, self_coord: Organ) -> None:
        """绑定器官坐标与 cat 弱引用。

        Args:
            cat: 所属猫实例（弱引用语义：器官不应改 cat 本体状态）
            self_coord: 本器官在 wiring 里的坐标 ``(category, name)``
        """
        self._cat_ref = cat
        self._self_coord = self_coord

    async def _signal_to(
        self,
        to: Organ,
        method: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """向目标器官发 signal（自动补 from_organ = ``self._self_coord``）。

        等价于 ``await self._cat_ref.signal(self._self_coord, to, method, ...)``
        但更短、不易拼错 from_organ。

        Raises:
            IllegalNeuralPathError: wiring 禁止该边、方法黑名单、或目标
                Protocol 未声明该方法（v0.5.11 新增契约校验）。
            OrganNotMountedError: 目标器官未挂载。
        """
        return await self._cat_ref.signal(
            self._self_coord, to, method, *args, **kwargs,
        )

    async def _probe(self, to: Organ) -> dict[str, Any]:
        """向目标器官发只读诊断探针（转发 ``cat.probe``）。

        probe 不是器官间通信（不走 wiring 边校验），任何已 wire 的器官
        都可以被 probe。

        Raises:
            IllegalNeuralPathError: 目标器官未在 wiring 中。
            TypeError: 目标未实现 Diagnosable 或 diagnose() 返回非 dict。
        """
        return await self._cat_ref.probe(to)


__all__ = ["OrganMixin"]
