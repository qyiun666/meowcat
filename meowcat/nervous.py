"""meowcat 神经系统 — Nervous 子系统（v0.5.9 抽离）。

通信约定（v0.5.20+）：
- signal(): 走 wiring 校验的正式通道
- probe(): 只读诊断，不校验 wiring 边
- inject(): Needle 对象的绕过校验写入（仅调试/admin）
- 直接调用: 允许。只要 wiring 表中有对应的边，
  不强制所有调用走 signal()。直接调用是性能优化。

真正要防止的是 wiring 表中不存在的 FORBIDDEN 路径。

职责：持有 :class:`Wiring`，通过 ``signal()`` 裁决器官互访、通过 ``probe()``
只读诊断器官。依赖显式注入的 :class:`OrganHost` + :class:`EventBus`，可独立
实例化给"只要信号系统、不要反射弧"的场景使用::

    host = OrganHost("toy")
    events = EventBus()
    nervous = Nervous(host, events)
    nervous.wire_default()
    host.mount("brain", "cerebrum", brain)
    host.mount("brain", "hippocampus", hippo)
    nervous.freeze()
    await nervous.signal(
        ("brain", "cerebrum"), ("brain", "hippocampus"),
        "remember", msg="hi",
    )

分身猫场景：构造时传入 ``forbidden_methods`` 禁用特定方法名::

    nervous = Nervous(
        host, events,
        forbidden_methods=frozenset({"spawn_kitten", "absorb_merge"}),
    )
    await nervous.signal(..., "spawn_kitten")  # -> IllegalNeuralPathError
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

import inspect
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Protocol

from meowcat.errors import IllegalNeuralPathError
from meowcat.events import EventBus
from meowcat.host import OrganHost
from meowcat.loop import NerveEvent
from meowcat.wiring import Organ, Wiring


# -- 信号中间件类型 --------------------------------------------------

@dataclass(frozen=True)
class SignalCall:
    """单次 signal() 调用的不可变上下文。"""
    from_organ: Organ
    to_organ: Organ
    method: str
    args: tuple[Any, ...]
    kwargs: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.monotonic)


class SignalMiddleware(Protocol):
    """信号中间件 — 每次 signal() 调用前后执行。

    所有方法均为可选实现：只实现需要的钩子即可。
    """

    async def before(self, ctx: SignalCall) -> SignalCall | None:
        """signal 执行前调用。返回 None 则短路（阻止执行）。

        返回 SignalCall 实例表示继续执行（可修改 ctx 但框架忽略修改值，
        当前版本仅支持 None 短路语义）。
        """
        ...

    async def after(self, ctx: SignalCall, result: Any) -> Any:
        """signal 执行成功后调用。可修改/包装返回值。"""
        ...

    async def on_error(self, ctx: SignalCall, error: Exception) -> None:
        """signal 抛出异常时调用。仅通知，异常继续向上传播。"""
        ...


@lru_cache(maxsize=None)
def _build_organ_spec_index() -> dict[Organ, "OrganSpec"]:  # noqa: F821
    """构建 ORGAN_SPECS 的坐标→规范 索引（缓存）。"""
    from meowcat.biology import ORGAN_SPECS  # noqa: PLC0415
    return {s.coord: s for s in ORGAN_SPECS}


def _get_organ_spec(organ: Organ) -> "OrganSpec | None":  # noqa: F821
    """根据器官坐标查找 ORGAN_SPECS 中的规范。"""
    return _build_organ_spec_index().get(organ)


@lru_cache(maxsize=None)
def _protocol_public_members(proto: type) -> frozenset[str]:
    """返回 Protocol 上声明的公开成员名集合（缓存）。

    用于 signal 契约校验：验证 `method` 是否在目标器官 Protocol 上声明。
    排除以 ``_`` 开头的 dunder/私有属性，仅保留业务 API 方法/字段。

    缓存使每 Protocol 类第一次校验后 ‘member set’ 常驻，
    后续 signal 热路径只做一次 dict 查找 + 一次 set in 查找。
    """
    return frozenset(
        name for name in dir(proto) if not name.startswith("_")
    )


class Nervous:
    """神经系统：signal 调度 + probe 诊断 + wiring 生命周期。"""

    def __init__(
        self,
        host: OrganHost,
        events: EventBus,
        *,
        forbidden_methods: frozenset[str] = frozenset(),
    ) -> None:
        """构造神经系统。

        Args:
            host: 器官容器（用于解析目标器官实例）
            events: 事件总线（用于 emit ``nerve.signal`` 便于调试埋点）
            forbidden_methods: 方法级黑名单。调 ``signal(..., method=X)``
                时 ``X in forbidden_methods`` 则抛 :class:`IllegalNeuralPathError`。
                分身猫用此机制禁用 ``spawn_kitten`` / ``absorb_merge`` 等主猫专属方法。
        """
        self.host = host
        self.events = events
        self.wiring = Wiring()
        self.forbidden_methods = forbidden_methods
        self._middleware: list[SignalMiddleware] = []

    # -- 神经突触 ------------------------------------------------------

    async def signal(
        self,
        from_organ: Organ,
        to_organ: Organ,
        method: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """器官互访的唯一合法通道。

        流程：

        1. **方法黑名单**：``method in forbidden_methods`` 抛
           :class:`IllegalNeuralPathError`
        2. **通路校验**：``wiring.assert_allowed(from, to)`` 非法抛
           :class:`IllegalNeuralPathError`
        3. emit ``nerve.signal`` 事件（便于调试/埋点）
        4. 从 ``host.organ(*to_organ)`` 取出目标器官
        5. ``getattr(target, method)(*args, **kwargs)``，若返回 awaitable
           自动 await

        Args:
            from_organ: 调用方器官坐标 ``(category, name)``
            to_organ: 目标器官坐标 ``(category, name)``
            method: 目标上要调用的方法名
            *args, **kwargs: 转发给目标方法

        Returns:
            目标方法的返回值（已 unwrap 过 awaitable）
        """
        if method in self.forbidden_methods:
            raise IllegalNeuralPathError(
                from_organ, to_organ,
                reason=f"forbidden method '{method}'",
            )

        self.wiring.assert_allowed(from_organ, to_organ)

        # v0.5.11 Protocol 契约校验：目标坐标有 Protocol 映射时，
        # 校验 method 在该 Protocol 上已声明。无映射时略过（保留自由度）。
        from meowcat.biology import ORGAN_PROTOCOLS  # noqa: PLC0415
        protocol = ORGAN_PROTOCOLS.get(to_organ)
        if protocol is not None and method not in _protocol_public_members(protocol):
            raise IllegalNeuralPathError(
                from_organ, to_organ,
                reason=(
                    f"method '{method}' not declared on "
                    f"{protocol.__name__} for organ {to_organ}"
                ),
            )

        # v0.5.26 方法级写权限：非 write_callers 调 write_method → 抛异常
        spec = _get_organ_spec(to_organ)
        if spec and method in spec.write_methods and from_organ not in spec.write_callers:
            raise IllegalNeuralPathError(
                from_organ, to_organ,
                reason=(
                    f"'{method}' is a write method on {to_organ}, "
                    f"only {spec.write_callers} can call it"
                ),
            )

        # 构造信号上下文
        ctx = SignalCall(
            from_organ=from_organ,
            to_organ=to_organ,
            method=method,
            args=args,
            kwargs=kwargs,
        )

        # before 链：任一返回 None 则短路
        for mw in self._middleware:
            if hasattr(mw, "before"):
                before_result = mw.before(ctx)
                if inspect.isawaitable(before_result):
                    before_result = await before_result
                if before_result is None:
                    return None

        await self.events.emit(
            NerveEvent.SIGNAL,
            {
                "from": from_organ,
                "to": to_organ,
                "method": method,
            },
        )

        target = self.host.organ(*to_organ)
        fn = getattr(target, method)
        try:
            result = fn(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result
        except Exception as exc:
            for mw in self._middleware:
                if hasattr(mw, "on_error"):
                    on_err = mw.on_error(ctx, exc)
                    if inspect.isawaitable(on_err):
                        await on_err
            raise

        # after 链：可修改/包装返回值
        for mw in self._middleware:
            if hasattr(mw, "after"):
                after_result = mw.after(ctx, result)
                if inspect.isawaitable(after_result):
                    result = await after_result
                else:
                    result = after_result

        return result

    # -- 听诊器 probe ------------------------------------------------

    async def probe(self, to_organ: Organ) -> dict[str, Any]:
        """只读诊断通路。

        CLI 作为听诊器，通过此方法监听已 wire 的器官状态。与 ``signal()`` 不同：

        - probe 没有 from_organ（CLI 不是器官），只校验 to_organ 已 wire
        - 仅允许调 ``diagnose()`` 方法（:class:`meowcat.protocols.Diagnosable`）
        - 不 emit 事件（诊断不算神经信号）
        - 返回值必须是 dict

        Args:
            to_organ: 目标器官坐标 ``(category, name)``

        Returns:
            器官 ``diagnose()`` 的 dict 快照

        Raises:
            OrganNotMountedError: 器官未挂载
            IllegalNeuralPathError: 器官未在 wiring 中
            TypeError: 器官未实现 Diagnosable 协议或 diagnose() 返回非 dict
        """
        from meowcat.protocols import Diagnosable  # noqa: PLC0415

        if not self.wiring.is_organ_wired(to_organ):
            raise IllegalNeuralPathError(
                ("_probe", "_probe"), to_organ,
                reason="organ not wired — probe only allowed on wired organs",
            )

        target = self.host.organ(*to_organ)

        if not isinstance(target, Diagnosable):
            raise TypeError(
                f"Organ {to_organ} does not implement Diagnosable protocol"
            )

        fn = getattr(target, "diagnose")
        result = fn()
        if inspect.isawaitable(result):
            result = await result

        if not isinstance(result, dict):
            raise TypeError(
                f"Organ {to_organ}.diagnose() must return dict, "
                f"got {type(result).__name__}"
            )

        return result

    # -- wiring 生命周期 ----------------------------------------------

    def wire_default(self) -> None:
        """一键装配生物学默认神经通路表。

        等价于 ``meowcat.biology.apply_default_wiring(self.wiring)``。
        可在任何时刻调用，可多次叠加（wiring 是 set，去重）。
        """
        from meowcat import biology  # noqa: PLC0415
        biology.apply_default_wiring(self.wiring)

    def freeze(self) -> None:
        """冻结 wiring。之后 ``wiring.connect/forbid`` 都会抛 :class:`MeowCatError`。

        注意：本方法**不校验 reflex**。reflex 与 wiring 的一致性校验由
        :class:`meowcat.reflex.ReflexArc.validate_paths` 负责。组合协调通常由
        :meth:`CatBase.freeze_nervous_system` 完成。
        """
        self.wiring.freeze()


__all__ = ["Nervous", "SignalCall", "SignalMiddleware"]
