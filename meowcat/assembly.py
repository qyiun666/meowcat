"""meowcat 装配骨架 — 猫的基类（v0.5.9 门面化）。

meowcat 定义猫的骨架和生命周期，meowagent 子类决定用什么材料的器官。

**v0.5.9 子系统解耦**：CatBase 不再是 440 行大类，而是 :class:`OrganHost` +
:class:`Nervous` + :class:`ReflexArc` + :class:`EventBus` 的组合者，并通过门面
方法保持 v0.5.0 以来的外部 API 100% 兼容。

五大子系统（每个都可独立实例化、可单飞）：

+----------------+---------------------------+----------------------+
| 子系统         | 职责                      | 可单飞               |
+================+===========================+======================+
| OrganHost      | 器官容器（mount/organ）    | ✓                    |
+----------------+---------------------------+----------------------+
| Wiring         | 通路图（纯数据结构）       | ✓                    |
+----------------+---------------------------+----------------------+
| Nervous        | signal + probe 调度        | ✓（需 host + events）|
+----------------+---------------------------+----------------------+
| ReflexArc      | perceive 反射入口          | ✓（需 events）       |
+----------------+---------------------------+----------------------+
| EventBus       | 事件总线                   | ✓（零依赖）          |
+----------------+---------------------------+----------------------+

CatBase 只做四件事：

1. **组合五大子系统**（``_host`` / ``_events`` / ``_nervous`` / ``_reflex``）
2. **门面转发**：外部调用 ``cat.mount/signal/perceive`` 自动路由到对应子系统
3. **生命周期**（``start`` / ``shutdown``）
4. **协调 freeze**：先 reflex 校验 path，再 wiring freeze

不做：具体器官实例化、配置加载、IO —— 这些都是 meowagent 的事。

**残疾猫是一等公民**：``CatBase("x", enable_wiring=False)`` 可以跑，
``enable_reflex=False`` 也可以跑，对应的 signal/perceive 会抛 RuntimeError
明确提示子系统未启用。
"""

from __future__ import annotations

from typing import Any, AsyncIterator

from meowcat.errors import IllegalNeuralPathError
from meowcat.events import EventBus, Handler
from meowcat.host import OrganHost
from meowcat.loop import Lifecycle
from meowcat.nervous import Nervous
from meowcat.reflex import Reflex, ReflexArc
from meowcat.tools.skill import SkillRegistry
from meowcat.tools.tool import ToolRegistry
from meowcat.wiring import Organ, Wiring


class CatBase:
    """猫装配基类（v0.5.9 组合者，v1.0.1 统一分身猫模型）。

    v1.0.1: 新增 ``parent_id`` / ``allowed_organs`` / ``forbidden_methods``，
    替代原 KittenBase 类。分身猫 = 一只带了 ``parent_id`` 且器官/方法权限受限
    的 CatBase。
    """

    def __init__(
        self,
        cat_id: str,
        *,
        parent_id: str | None = None,
        allowed_organs: frozenset[str] | None = None,
        forbidden_methods: frozenset[str] = frozenset(),
        enable_wiring: bool = True,
        enable_reflex: bool = True,
    ) -> None:
        """构造猫骨架。

        Args:
            cat_id: 猫唯一标识
            parent_id: 父猫标识（纯字符串，不做对象引用）。用于追踪和结果回传路由。
            allowed_organs: 允许访问的器官属性名集合。``None`` = 全部允许（默认）。
                有值时 ``__getattribute__`` 拦截禁止器官访问。
            forbidden_methods: 方法级黑名单。``signal(..., method=X)``
                时 ``X in forbidden_methods`` 则抛 :class:`IllegalNeuralPathError`。
                分身猫用此禁用 ``spawn_kitten`` / ``absorb_merge`` 等主猫专属方法。
            enable_wiring: False 时不创建 Nervous 子系统，``signal/probe``
                调用会抛 RuntimeError。适合"裸容器"场景。
            enable_reflex: False 时不创建 ReflexArc 子系统，``perceive/
                register_reflex`` 调用会抛 RuntimeError。适合"只走 signal、
                不走 reflex"场景。
        """
        self._parent_id = parent_id
        # v1.0.1: 先设 _allowed_organs=None 避免 __init__ 内部 self.xxx
        # 赋值被 __getattribute__ 拦截；末尾再设为真实值。
        self._allowed_organs: frozenset[str] | None = None
        self._host = OrganHost(cat_id)
        self._events = EventBus()
        self._nervous: Nervous | None = (
            Nervous(self._host, self._events,
                    forbidden_methods=forbidden_methods)
            if enable_wiring else None
        )
        self._reflex: ReflexArc | None = (
            ReflexArc(self._events, self._nervous) if enable_reflex else None
        )
        # v0.5.23: 工具/Skill 注册中心 — 每只猫都有爪子
        self.tool_registry = ToolRegistry()
        self.skill_registry = SkillRegistry()
        # v0.5.27: 路径注册中心 — 原子路径表
        from meowcat.path import PathRegistry, register_builtin_paths  # noqa: PLC0415
        self.path_registry = PathRegistry()
        register_builtin_paths(self.path_registry)
        # v0.5.28a: 链路注册中心 — Path 序列组合
        from meowcat.chain import ChainRegistry, register_builtin_chains  # noqa: PLC0415
        self.chain_registry = ChainRegistry()
        register_builtin_chains(self.chain_registry)
        # v0.5.28b: 闭环注册中心 — Chain + 触发/退出事件
        from meowcat.loops import LoopRegistry, register_default_loops  # noqa: PLC0415
        self.loop_registry = LoopRegistry()
        register_default_loops(self.loop_registry, self.chain_registry)
        # v1.0.4: 元闭环注册中心 — Loop 序列组合
        from meowcat.loops import LoopSequenceRegistry  # noqa: PLC0415
        self.loopseq_registry = LoopSequenceRegistry()
        # v1.0.1: allowed_organs 必须在所有属性设置完之后才赋值，
        # 避免 __init__ 内部 self.xxx 赋值被 __getattribute__ 拦截
        self._allowed_organs = allowed_organs

    # -- 只读门面属性 ------------------------------------------------

    @property
    def parent_id(self) -> str | None:
        """父猫标识（纯字符串，无对象引用）。"""
        return self._parent_id

    @property
    def cat_id(self) -> str:
        """猫唯一标识（从 ``_host`` 读取）。"""
        return self._host.cat_id

    @property
    def wiring(self) -> Wiring:
        """神经通路图（Nervous 禁用时抛 :class:`AttributeError`）。"""
        if self._nervous is None:
            raise AttributeError(
                "wiring disabled — construct with enable_wiring=True",
            )
        return self._nervous.wiring

    @property
    def reflexes(self) -> "ReflexRegistry":
        """反射注册表（ReflexArc 禁用时抛 :class:`AttributeError`）。"""
        if self._reflex is None:
            raise AttributeError(
                "reflex disabled — construct with enable_reflex=True",
            )
        return self._reflex.registry

    @property
    def events(self) -> EventBus:
        """事件总线（永远可用）。"""
        return self._events

    # -- 器官容器门面 ------------------------------------------------

    def mount(
        self,
        category: str,
        name: str,
        organ: Any,
        *,
        protocol: type | None = None,
    ) -> None:
        """挂载器官（转发到 :class:`OrganHost`）。"""
        self._host.mount(category, name, organ, protocol=protocol)

    def organ(self, category: str, name: str) -> Any:
        """取出器官（转发到 :class:`OrganHost`）。"""
        return self._host.organ(category, name)

    def organs(self, category: str) -> dict[str, Any]:
        """分类下所有器官快照。"""
        return self._host.organs(category)

    def has_organ(self, category: str, name: str) -> bool:
        """检查器官是否已挂载。"""
        return self._host.has_organ(category, name)

    def unmount(self, category: str, name: str) -> bool:
        """卸载器官。"""
        return self._host.unmount(category, name)

    def assert_organs_mounted(
        self, required: list[tuple[str, str]],
    ) -> None:
        """断言必需器官已挂载。"""
        self._host.assert_organs_mounted(required)

    # -- 事件门面 ----------------------------------------------------

    def on(self, event: str, handler: Handler | None = None) -> Any:
        """注册事件 handler。"""
        return self._events.on(event, handler)

    def off(self, event: str, handler: Handler) -> bool:
        """注销事件 handler。"""
        return self._events.off(event, handler)

    async def emit(self, event: str, payload: Any = None) -> None:
        """触发事件。"""
        await self._events.emit(event, payload)

    # -- 器官属性访问控制 (v1.0.1) -----------------------------------

    def __getattribute__(self, name: str) -> Any:
        """拦截禁止器官名的直接访问。

        ``allowed_organs`` 为 None 时全部放行（默认）。
        有值时非 ``_`` 前缀、不在允许集合中、也不在 ``_ALWAYS_ALLOWED`` 中的
        属性名抛 :class:`IllegalNeuralPathError`。

        热路径：``_`` 前缀私有属性零开销跳过 → O(1) frozenset 查找。
        """
        if name.startswith('_'):
            return super().__getattribute__(name)
        allowed = super().__getattribute__('_allowed_organs')
        if allowed is not None and name not in allowed:
            if name not in CatBase._ALWAYS_ALLOWED:
                raise IllegalNeuralPathError(
                    ("_cat", "_cat"), ("_cat", name),
                    reason=(
                        f"猫 '{super().__getattribute__('cat_id')}' "
                        f"无权访问 '{name}' 器官。"
                    ),
                )
        return super().__getattribute__(name)

    _ALWAYS_ALLOWED: frozenset[str] = frozenset({
        "cat_id", "parent_id",
        "tool_registry", "skill_registry",
        "path_registry", "chain_registry", "loop_registry",
        "loopseq_registry",
        "wiring", "reflexes", "events",
    })

    # -- 神经突触门面 ------------------------------------------------

    async def signal(
        self,
        from_organ: Organ,
        to_organ: Organ,
        method: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """器官互访（转发到 :class:`Nervous`）。

        Raises:
            RuntimeError: ``enable_wiring=False`` 时子系统未启用。
        """
        if self._nervous is None:
            raise RuntimeError(
                "signal unavailable — cat was constructed with enable_wiring=False",
            )
        return await self._nervous.signal(
            from_organ, to_organ, method, *args, **kwargs,
        )

    async def probe(self, to_organ: Organ) -> dict[str, Any]:
        """只读诊断（转发到 :class:`Nervous`）。"""
        if self._nervous is None:
            raise RuntimeError(
                "probe unavailable — cat was constructed with enable_wiring=False",
            )
        return await self._nervous.probe(to_organ)

    # -- 神经系统装配 ------------------------------------------------

    def wire_default_nervous_system(self) -> None:
        """装配默认神经通路表。``enable_wiring=False`` 时 no-op。"""
        if self._nervous is None:
            return
        self._nervous.wire_default()

    def register_reflex(self, reflex: Reflex) -> None:
        """注册反射弧。"""
        if self._reflex is None:
            raise RuntimeError(
                "register_reflex unavailable — enable_reflex=False",
            )
        self._reflex.register(reflex)

    def freeze_nervous_system(self) -> None:
        """冻结神经系统：先校验 reflex.path 合法、再冻结 wiring。

        协调顺序很关键：reflex.validate_paths 需要读取 ``nervous.wiring``，
        一旦 wiring freeze 后仍可读，所以顺序理论上可互换，这里采取"先校验、
        再冻结"的保守顺序，便于未来 freeze 改为清理 wiring 临时状态时也安全。
        """
        if self._reflex is not None:
            self._reflex.validate_paths()
        if self._nervous is not None:
            self._nervous.freeze()

    # -- 感知入口 ----------------------------------------------------

    async def perceive(
        self,
        input: Any,
        **extras: Any,
    ) -> AsyncIterator[Any]:
        """猫对外的唯一反射入口（转发到 :class:`ReflexArc`）。

        Raises:
            RuntimeError: ``enable_reflex=False`` 时子系统未启用。
            NoReflexMatchedError: 无反射命中 ``input``。
        """
        if self._reflex is None:
            raise RuntimeError(
                "perceive unavailable — enable_reflex=False",
            )
        async for ev in self._reflex.perceive(input, cat=self, **extras):
            yield ev

    # -- 装配工具 ----------------------------------------------------

    def _assemble(
        self,
        *,
        reflex_stages: list[Any] | None = None,
        reflexes: list[Reflex] | None = None,
    ) -> None:
        """自动扫描 ``self`` 上的器官属性并完成骨架装配。

        v0.5.9: 实际逻辑在顶层函数 :func:`assemble_default_cat` 中，此方法
        仅作为薄包装保持向后兼容。子类（如 meowagent.Cat）只需在 ``__init__``
        末尾继续调 ``self._assemble(reflex_stages=[...])``，行为不变。

        v0.5.20: 新增 ``reflexes`` 参数，透传给 ``assemble_default_cat()``。

        v0.5.21: ``assemble_default_cat()`` 不再 freeze，由本方法负责。

        Args:
            reflex_stages: 默认 text_dialogue reflex 的 stages 列表。
                           为 None 则使用空列表。
            reflexes: 反射弧列表，None 时不注册任何 reflex。
        """
        assemble_default_cat(
            self, reflex_stages=reflex_stages, reflexes=reflexes)
        self.freeze_nervous_system()

    # -- 诊断快捷方法 ------------------------------------------------

    async def health_check(self) -> dict[str, Any]:
        """全身体检 — 返回所有器官的诊断快照。

        快捷方式，等价于 ``Stethoscope.probe_all(self)``。

        Returns:
            ``{"brain:hippocampus": {...}, "sense:ears": {...}, ...}``
        """
        from meowcat.diagnose import Stethoscope  # noqa: PLC0415
        return await Stethoscope.probe_all(self)

    async def brain_check(self) -> dict[str, Any]:
        """只检查大脑区域器官。

        快捷方式，等价于 ``Stethoscope.probe_category(self, "brain")``。

        Returns:
            ``{"hippocampus": {...}, "cerebrum": {...}, ...}``
        """
        from meowcat.diagnose import Stethoscope  # noqa: PLC0415
        return await Stethoscope.probe_category(self, "brain")

    def wiring_diagram(self, format: str = "mermaid") -> str:
        """生成 wiring 图的可视化字符串。

        wiring 禁用时抛 :class:`AttributeError`。

        Args:
            format: ``"mermaid"`` 或 ``"dot"``

        Returns:
            mermaid 或 dot 格式的图描述字符串

        Examples:

            >>> print(cat.wiring_diagram())
            >>> print(cat.wiring_diagram(format="dot"))
        """
        from meowcat.diagnose import render_wiring  # noqa: PLC0415
        # 收集所有已挂载器官作为孤立节点检测的输入
        mounted: frozenset[Organ] = frozenset(self._host.list_all_organs())
        return render_wiring(self.wiring, format=format, organs=mounted)

    # -- 生命周期 ----------------------------------------------------

    async def start(self) -> None:
        """启动猫。子类可重写，**务必调用 ``await super().start()``**。"""
        await self._events.emit(Lifecycle.START, {"cat": self})

    async def shutdown(self) -> None:
        """关闭猫。子类可重写，**务必调用 ``await super().shutdown()``**。"""
        await self._events.emit(Lifecycle.SHUTDOWN, {"cat": self})

    # -- 闭环执行 ----------------------------------------------------

    async def run_loop(self, name: str, **initial_input: Any) -> dict[str, Any]:
        """执行一个闭环：触发事件 → 跑 chain → 退出事件。

        等价于::

            self.loop_registry.run(self, name, **initial_input)

        Args:
            name: 闭环名称（如 ``"conversation"``）
            **initial_input: 初始输入，传入 chain 的第一步

        Returns:
            chain 执行结果（dict）

        Raises:
            KeyError: 闭环不存在

        Examples:

            result = await cat.run_loop("conversation", message="你好")
        """
        return await self.loop_registry.run(self, name, **initial_input)

    # -- 元闭环执行 (v1.0.4) -----------------------------------------

    async def run_loopseq(self, name: str, **initial_input: Any) -> dict[str, Any]:
        """执行一个元闭环：组合多个 Loop 顺序或并发执行。

        等价于::

            self.loopseq_registry.run(self, name, **initial_input)

        Args:
            name: 元闭环名称（如 ``"daily_maintenance"``）
            **initial_input: 初始输入

        Returns:
            最后一步结果（sequential）或 ``{loop_name: result, ...}``
            （event_driven）

        Raises:
            KeyError: 元闭环不存在

        Examples:

            result = await cat.run_loopseq("daily_maintenance")
        """
        return await self.loopseq_registry.run(self, name, **initial_input)

    # -- CLI 门面方法 (v1.0.9) ---------------------------------------

    async def search_memory(self, query: str, limit: int = 5) -> dict[str, Any]:
        """搜索记忆。等价于 ``/search <query>``。

        执行 ``memory_search`` 链（locate path），从海马体中检索相关记忆。

        Args:
            query: 搜索关键词
            limit: 返回结果上限

        Returns:
            记忆检索结果 dict
        """
        return await self.chain_registry.run(
            self, "memory_search", msg=query, session_id=self.cat_id,
        )

    async def memory_stats(self) -> dict[str, Any]:
        """记忆统计。等价于 ``/stats``。

        通过 signal 调用海马体的 ``stats`` 方法获取记忆统计信息。

        Returns:
            记忆统计 dict
        """
        from meowcat.anatomy import BRAINSTEM, HIPPOCAMPUS  # noqa: PLC0415
        result = await self.signal(BRAINSTEM, HIPPOCAMPUS, "stats")
        if isinstance(result, dict):
            return result
        return {"stats": result}

    async def run_maintenance(
        self, country_code: str | None = None,
    ) -> dict[str, Any]:
        """运行维护。等价于 ``/maintenance``。

        执行 ``daily_maintenance`` 元闭环（自维护后体检）。

        Args:
            country_code: 可选的国家代码，用于按区域衰减策略

        Returns:
            维护结果 dict
        """
        return await self.run_loopseq(
            "daily_maintenance",
        )


def mount_known_organs(cat: CatBase) -> None:
    """扫描 cat 上的已知器官属性并 mount 到 OrganHost。

    覆盖 brain / sense / voice 三类核心器官。Growth 器官由应用层自行挂载。
    ``factory.create_cat()`` 和 ``assemble_default_cat()`` 共用此函数，
    消灭两处重复的器官名列表。

    Args:
        cat: 已设置器官属性的 CatBase 实例
    """
    _BRAIN_NAMES = {
        "hippocampus", "thalamus", "amygdala", "frontal",
        "hypothalamus", "cerebellum", "cerebrum", "brainstem", "cortex",
    }
    _SENSE_NAMES = {"ears", "eyes", "whiskers", "paws"}
    _VOICE_NAMES = {"mouth", "purr", "tail"}

    for name in _BRAIN_NAMES:
        organ = getattr(cat, name, None)
        if organ is not None:
            cat.mount("brain", name, organ)

    for name in _SENSE_NAMES:
        organ = getattr(cat, name, None)
        if organ is not None:
            cat.mount("sense", name, organ)

    for name in _VOICE_NAMES:
        organ = getattr(cat, name, None)
        if organ is not None:
            cat.mount("voice", name, organ)


# -- 顶层装配函数（v0.5.9 新增）-------------------------------------

def assemble_default_cat(
    cat: CatBase,
    *,
    reflex_stages: list[Any] | None = None,
    reflexes: list[Reflex] | None = None,
) -> None:
    """一键装配默认猫：扫描器官属性 → mount → wire → register reflex。

    v0.5.21: 不再调用 freeze_nervous_system()，由调用方控制冻结时机。
    调用方可在 wiring + reflex 注册完成后自行 freeze。

    流程：

    1. 扫描 ``cat`` 上的已知器官属性名 ``mount`` 到 host
    2. ``cat.wire_default_nervous_system()`` 装配生物学默认通路
    3. 注册 reflex（调用方传入）

    Args:
        cat: 已设置器官属性的 CatBase 实例
        reflex_stages: 默认 text_dialogue reflex 的 stages 列表
                        （仅当 reflexes 中有 text_dialogue 时生效）
        reflexes: 反射弧列表，None 时不注册任何 reflex
    """
    mount_known_organs(cat)
    cat.wire_default_nervous_system()

    # v0.5.23: 注册通用内置工具（每只猫都需要的基础工具）
    from meowcat.tools.builtin import BUILTIN_TOOLS  # noqa: PLC0415
    for t in BUILTIN_TOOLS:
        cat.tool_registry.register(t)

    # 反射弧（调用方传入）
    if reflexes:
        for ref in reflexes:
            # 如果有 reflex_stages 且是 text_dialogue，注入 stages
            if ref.name == "text_dialogue" and reflex_stages is not None:
                ref = Reflex(
                    name=ref.name,
                    trigger=ref.trigger,
                    path=ref.path,
                    priority=ref.priority,
                    stages=list(reflex_stages),
                )
            cat.register_reflex(ref)


__all__ = ["CatBase", "assemble_default_cat", "mount_known_organs"]
