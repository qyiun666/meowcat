"""v0.5.9 — 残疾猫一等公民：enable_wiring=False / enable_reflex=False 构造。"""

from __future__ import annotations

import anyio
import pytest

from meowcat.testing import make_cat
from meowcat import CatBase


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
