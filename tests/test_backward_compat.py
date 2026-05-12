# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""v0.5.9 向后兼容 / 子系统独立测试（合并自 5 个 test_v059_* 文件）。

覆盖:
  * 向后兼容契约 — v0.5.0~v0.5.8 旧 API
  * 残疾猫一等公民 — enable_wiring=False / enable_reflex=False
  * OrganHost 独立 — 容器语义，不依赖 Nervous/ReflexArc
  * Nervous 独立 — 依赖 OrganHost + EventBus
  * ReflexArc 独立 — 只依赖 EventBus
"""

from __future__ import annotations

import anyio
import pytest

from meowcat import (
    assemble_default_cat,
    biology,
    EventBus,
    Nervous,
    OrganHost,
    Reflex,
    ReflexArc,
)
from meowcat.errors import (
    IllegalNeuralPathError,
    NoReflexMatchedError,
    OrganNotMountedError,
    OrganProtocolMismatchError,
    ReflexPathInvalidError,
)
from meowcat.protocols import OrganProtocol
from meowcat.testing import make_cat

# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════


class _Cerebrum:
    name = "cerebrum"

    async def generate(self, p, system_prompt=None,
                       temperature=0.7, max_tokens=None) -> str:
        return "meow"

    async def stream_generate(self, p, system_prompt=None,
                              temperature=0.7, max_tokens=None):
        yield "meow"

    def reload_config(self) -> None: ...


class _Ears:
    name = "ears"

    def diagnose(self) -> dict:  # type: ignore[type-arg]
        return {}


class _Bad:
    pass  # 无 name 属性，不满足 OrganProtocol


class _Organ:
    def __init__(self, name: str) -> None:
        self.name = name

    async def echo(self, msg: str) -> str:
        return f"{self.name}:{msg}"


def _build_triplet(cat_uid: str = "n") -> tuple[OrganHost, EventBus, Nervous]:
    host = OrganHost(cat_uid)
    events = EventBus()
    nervous = Nervous(host, events)
    return host, events, nervous


def _trig_str(x: object) -> bool:
    return isinstance(x, str)


# ═══════════════════════════════════════════════════════════════════════
# 向后兼容契约
# ═══════════════════════════════════════════════════════════════════════


def test_catbase_legacy_single_arg_ctor() -> None:
    """v0.5.0 风格：只传 cat_uid 即可（现为 name）。"""
    cat = make_cat("legacy")
    assert cat.name == "legacy"
    assert cat.cat_uid is not None


def test_catbase_exposes_wiring_and_reflexes_property() -> None:
    """v0.5.x 旧代码会读 ``cat.wiring`` / ``cat.reflexes``。"""
    cat = make_cat("x")
    assert cat.wiring is not None
    assert cat.reflexes is not None


def test_catbase_assemble_still_works() -> None:
    """agent.py#L165 依赖 ``self._assemble(reflex_stages=...)``。

    v0.5.20: assemble 不再自动注册 reflex，调用方需显式传入 reflexes。
    """
    cat = make_cat("x")
    cat.cerebrum = _Cerebrum()  # type: ignore[attr-defined]
    cat._assemble()
    assert cat.has_organ("brain", "cerebrum")
    assert cat.wiring.frozen is True


def test_assemble_default_cat_top_level() -> None:
    """v0.5.9 新：可不依赖 ``_assemble`` 方法，直接调用顶层函数。

    v0.5.21: assemble_default_cat() 不再 freeze，由调用方负责。
    """
    cat = make_cat("x")
    cat.cerebrum = _Cerebrum()  # type: ignore[attr-defined]
    assemble_default_cat(cat)
    cat.freeze_nervous_system()
    assert cat.has_organ("brain", "cerebrum")
    assert cat.wiring.frozen is True


def test_catbase_parent_id_and_forbidden_methods():
    """v1.0.1: CatBase 支持 parent_id / forbidden_methods（替代 KittenBase）。"""
    cat = make_cat(
        "k1",
        parent_id="main",
        forbidden_methods=frozenset({"spawn_kitten", "absorb_merge"}),
    )
    assert cat.parent_id == "main"
    cat.mount("brain", "a", object())
    cat.mount("brain", "b", object())
    with pytest.raises(IllegalNeuralPathError):
        anyio.run(
            cat.signal,
            ("brain", "a"), ("brain", "b"), "spawn_kitten",
        )


def test_catbase_allowed_organs_blocks_access():
    """v1.0.1: allowed_organs 拦截禁止器官名的直接访问。"""
    cat = make_cat(
        "k1",
        allowed_organs=frozenset({"cerebellum", "cerebrum"}),
    )
    # allowed 属性可以访问（不存在所以 AttributeError）
    try:
        _ = cat.cerebrum
    except AttributeError:
        pass  # 未设置，预期抛 AttributeError 而非 IllegalNeuralPathError
    # 禁止属性抛 IllegalNeuralPathError
    with pytest.raises(IllegalNeuralPathError):
        _ = cat.hippocampus


# ═══════════════════════════════════════════════════════════════════════
# 残疾猫一等公民
# ═══════════════════════════════════════════════════════════════════════


def test_cat_disabled_wiring_still_mounts() -> None:
    cat = make_cat("c", enable_wiring=False)
    cat.mount("brain", "a", object())
    assert cat.has_organ("brain", "a")


def test_cat_disabled_wiring_raises_on_signal() -> None:
    cat = make_cat("c", enable_wiring=False)
    cat.mount("brain", "a", type("A", (), {"echo": lambda self, x: x})())
    cat.mount("brain", "b", object())
    with pytest.raises(RuntimeError):
        anyio.run(
            cat.signal,
            ("brain", "a"), ("brain", "b"), "echo", "hi",
        )


def test_cat_disabled_wiring_accessing_wiring_raises() -> None:
    cat = make_cat("c", enable_wiring=False)
    with pytest.raises(AttributeError):
        _ = cat.wiring


def test_cat_disabled_reflex_raises_on_perceive() -> None:
    cat = make_cat("c", enable_reflex=False)

    async def drive() -> None:
        async for _ in cat.perceive("hi"):
            pass

    with pytest.raises(RuntimeError):
        anyio.run(drive)


def test_cat_disabled_reflex_accessing_reflexes_raises() -> None:
    cat = make_cat("c", enable_reflex=False)
    with pytest.raises(AttributeError):
        _ = cat.reflexes


def test_cat_disabled_both_subsystems_survives_init() -> None:
    """两个都关，容器 + 事件仍可用。"""
    cat = make_cat("c", enable_wiring=False, enable_reflex=False)
    assert cat.name == "c"
    cat.mount("brain", "a", object())
    assert cat.has_organ("brain", "a")


# ═══════════════════════════════════════════════════════════════════════
# OrganHost 独立
# ═══════════════════════════════════════════════════════════════════════


def test_host_init_has_uid() -> None:
    host = OrganHost("cat-1")
    assert host.uid == "cat-1"


def test_mount_and_organ_roundtrip() -> None:
    host = OrganHost("cat")
    e = _Ears()
    host.mount("sense", "ears", e)
    assert host.organ("sense", "ears") is e


def test_organ_not_mounted_raises() -> None:
    host = OrganHost("cat")
    with pytest.raises(OrganNotMountedError):
        host.organ("brain", "nonexistent")


def test_mount_with_protocol_pass() -> None:
    host = OrganHost("cat")
    host.mount("sense", "ears", _Ears(), protocol=OrganProtocol)


def test_mount_with_protocol_fail() -> None:
    host = OrganHost("cat")
    with pytest.raises(OrganProtocolMismatchError):
        host.mount("sense", "ears", _Bad(), protocol=OrganProtocol)


def test_has_organ_and_unmount() -> None:
    host = OrganHost("cat")
    host.mount("sense", "ears", _Ears())
    assert host.has_organ("sense", "ears")
    assert host.unmount("sense", "ears")
    assert not host.has_organ("sense", "ears")
    assert not host.unmount("sense", "ears")  # 幂等


def test_organs_returns_snapshot_copy() -> None:
    host = OrganHost("cat")
    host.mount("sense", "ears", _Ears())
    snap = host.organs("sense")
    snap["eyes"] = object()
    assert not host.has_organ("sense", "eyes")  # 原数据未被污染


def test_assert_organs_mounted_ok() -> None:
    host = OrganHost("cat")
    host.mount("brain", "a", _Ears())
    host.mount("brain", "b", _Ears())
    host.assert_organs_mounted([("brain", "a"), ("brain", "b")])


def test_assert_organs_mounted_raises() -> None:
    host = OrganHost("cat")
    host.mount("brain", "a", _Ears())
    with pytest.raises(OrganNotMountedError):
        host.assert_organs_mounted([("brain", "missing")])


# ═══════════════════════════════════════════════════════════════════════
# Nervous 独立
# ═══════════════════════════════════════════════════════════════════════


def test_nervous_init_creates_empty_wiring() -> None:
    _, _, nervous = _build_triplet()
    assert nervous.wiring is not None
    assert not nervous.wiring.frozen


def test_nervous_signal_awaits_async() -> None:
    # v0.5.11: signal 增加 Protocol 契约校验。本测试只验证 async unwrap 行为，
    # 故改用未映射坐标避免契约层误伤（_Organ.echo 不在 ThalamusProtocol 上）
    host, _, nervous = _build_triplet()
    host.mount("sense", "ears", _Organ("ears"))
    host.mount("brain", "custom", _Organ("custom"))
    biology.apply_default_wiring(nervous.wiring)
    nervous.wiring.connect(("sense", "ears"), ("brain", "custom"))

    result = anyio.run(
        nervous.signal,
        ("sense", "ears"), ("brain", "custom"),
        "echo", "hi",
    )
    assert result == "custom:hi"


def test_nervous_signal_rejects_illegal_path() -> None:
    host, _, nervous = _build_triplet()
    host.mount("sense", "ears", _Organ("ears"))
    host.mount("sense", "paws", _Organ("paws"))
    biology.apply_default_wiring(nervous.wiring)

    with pytest.raises(IllegalNeuralPathError):
        anyio.run(
            nervous.signal,
            ("sense", "ears"), ("sense", "paws"),
            "echo", "boom",
        )


def test_nervous_forbidden_methods_block() -> None:
    host, _, nervous = _build_triplet()
    nervous = Nervous(
        host, EventBus(),
        forbidden_methods=frozenset({"spawn_kitten"}),
    )
    host.mount("brain", "a", _Organ("a"))
    host.mount("brain", "b", _Organ("b"))
    biology.apply_default_wiring(nervous.wiring)

    # 即使路径合法，禁止方法也直接被拦
    with pytest.raises(IllegalNeuralPathError):
        anyio.run(
            nervous.signal,
            ("brain", "a"), ("brain", "b"),
            "spawn_kitten",
        )


def test_nervous_wire_default_applies_biology() -> None:
    _, _, nervous = _build_triplet()
    assert len(nervous.wiring.edges()) == 0
    nervous.wire_default()
    assert len(nervous.wiring.edges()) > 0


def test_nervous_freeze_locks_wiring() -> None:
    _, _, nervous = _build_triplet()
    nervous.wire_default()
    nervous.freeze()
    assert nervous.wiring.frozen is True


# ═══════════════════════════════════════════════════════════════════════
# ReflexArc 独立
# ═══════════════════════════════════════════════════════════════════════


def test_reflex_arc_init_empty() -> None:
    arc = ReflexArc(EventBus())
    assert arc.match("anything") is None


def test_reflex_arc_register_and_match() -> None:
    arc = ReflexArc(EventBus())
    arc.register(Reflex(
        name="r1", trigger=_trig_str,
        path=(("sense", "ears"), ("brain", "thalamus")),
    ))
    r = arc.match("hello")
    assert r is not None and r.name == "r1"


def test_reflex_arc_validate_without_nervous_noop() -> None:
    arc = ReflexArc(EventBus(), nervous=None)
    arc.register(Reflex(
        name="r1", trigger=_trig_str,
        path=(("sense", "ears"), ("brain", "nonexistent")),
    ))
    # 无 nervous → 不校验，不抛
    arc.validate_paths()


def test_reflex_arc_validate_with_nervous_catches_bad_path() -> None:
    host = OrganHost("t")
    events = EventBus()
    nervous = Nervous(host, events)
    biology.apply_default_wiring(nervous.wiring)

    arc = ReflexArc(events, nervous=nervous)
    arc.register(Reflex(
        name="bad", trigger=_trig_str,
        path=(("sense", "ears"), ("sense", "paws")),  # 默认 wiring 里没有
    ))
    with pytest.raises(ReflexPathInvalidError):
        arc.validate_paths()


def test_reflex_arc_perceive_no_match_raises() -> None:
    arc = ReflexArc(EventBus())

    async def drive() -> None:
        async for _ in arc.perceive(123):  # int 不命中 str trigger
            pass

    with pytest.raises(NoReflexMatchedError):
        anyio.run(drive)
