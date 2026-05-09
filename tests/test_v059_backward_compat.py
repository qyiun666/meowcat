# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""v0.5.9 — 向后兼容契约：v0.5.0~v0.5.8 旧 API 保持一字不改。

锚点：meowagent/cat/agent.py#L75 ``super().__init__(cat_uid)``
       meowagent/cat/agent.py#L165 ``self._assemble(reflex_stages=[...])``
"""

from __future__ import annotations

import anyio

from meowcat import assemble_default_cat
from meowcat.testing import make_cat


class _Cerebrum:
    name = "cerebrum"

    async def generate(self, p, system_prompt=None,
                       temperature=0.7, max_tokens=None) -> str:
        return "meow"

    async def stream_generate(self, p, system_prompt=None,
                              temperature=0.7, max_tokens=None):
        yield "meow"

    def reload_config(self) -> None: ...


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
    import pytest

    from meowcat.errors import IllegalNeuralPathError

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
    import pytest

    from meowcat.errors import IllegalNeuralPathError

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

