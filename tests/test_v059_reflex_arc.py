# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""v0.5.9 — ReflexArc 独立测试。

ReflexArc 只依赖 EventBus，Nervous 可选传入用于 path 校验。
"""

from __future__ import annotations

import pytest

from meowcat import EventBus, Nervous, OrganHost, Reflex, ReflexArc, biology
from meowcat.errors import NoReflexMatchedError, ReflexPathInvalidError


def _trig_str(x: object) -> bool:
    return isinstance(x, str)


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
    import anyio

    arc = ReflexArc(EventBus())

    async def drive() -> None:
        async for _ in arc.perceive(123):  # int 不命中 str trigger
            pass

    with pytest.raises(NoReflexMatchedError):
        anyio.run(drive)

