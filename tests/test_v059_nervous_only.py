"""v0.5.9 — Nervous 独立测试。

Nervous 依赖 OrganHost + EventBus，但不依赖 CatBase / ReflexArc。
"""

from __future__ import annotations

import anyio
import pytest

from meowcat import EventBus, Nervous, OrganHost, biology
from meowcat.errors import IllegalNeuralPathError


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
