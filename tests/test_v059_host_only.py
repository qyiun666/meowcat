"""v0.5.9 — OrganHost 独立测试。

子系统单飞契约：不依赖 Nervous / ReflexArc / EventBus，纯容器语义。
"""

from __future__ import annotations

import pytest

from meowcat import OrganHost
from meowcat.errors import (
    OrganNotMountedError,
    OrganProtocolMismatchError,
)
from meowcat.protocols import OrganProtocol


class _Ears:
    name = "ears"

    def diagnose(self) -> dict:  # type: ignore[type-arg]
        return {}


class _Bad:
    pass  # 无 name 属性，不满足 OrganProtocol


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
