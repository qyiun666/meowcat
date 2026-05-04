"""meowcat 独立测试: CatBase mount/signal/perceive/_assemble 基础流程。

验证:
- mount / organ / unmount / has_organ / organs / assert_organs_mounted
- mount 带 Protocol 校验 / 不匹配抛 OrganProtocolMismatchError
- signal 合法调用 / 非法抛 IllegalNeuralPathError / awaitable 自动 await
- perceive 入口 / 无 reflex 抛 NoReflexMatchedError
- _assemble 自动装配 / wire_default / freeze
- CatBase signal forbidden_methods 黑名单
"""

from __future__ import annotations

import pytest

from meowcat.testing import make_cat
from meowcat import CatBase
from meowcat.errors import (
    IllegalNeuralPathError,
    NoReflexMatchedError,
    OrganNotMountedError,
    OrganProtocolMismatchError,
    StandaloneCatError,
)
from meowcat.protocols import AmygdalaProtocol, OrganProtocol
from meowcat.reflex import Reflex


# -- v1.1.3: CatBase 强制归属 ------------------------------------------

def test_catbase_without_container_raises():
    """CatBase 未传 container → StandaloneCatError"""
    with pytest.raises(StandaloneCatError):
        CatBase("orphan")


def test_catbase_with_container_ok():
    """CatBase 传 container → 正常创建"""
    from meowcat.colony import Colony
    from meowcat.defaults import InMemorySharedStore
    colony = Colony("test", storage=InMemorySharedStore())
    cat = CatBase("test", container=colony)
    assert cat.cat_id == "test"
    assert cat.container is colony
    assert cat.cat_address == "test/test-test"
    assert cat.cat_uid == "test"  # fallback when not created via Colony.create_cat()


# -- CatBase 器官管理 -----------------------------------------------


class TestCatBaseOrgans:
    """CatBase mount / organ / unmount / has_organ / organs 契约。"""

    def test_mount_and_organ(self) -> None:
        cat = make_cat("test")
        sentinel = object()
        cat.mount("brain", "hippocampus", sentinel)
        assert cat.organ("brain", "hippocampus") is sentinel

    def test_organ_not_mounted_raises(self) -> None:
        cat = make_cat("test")
        with pytest.raises(OrganNotMountedError) as exc:
            cat.organ("brain", "nonexistent")
        assert exc.value.category == "brain"
        assert exc.value.name == "nonexistent"

    def test_has_organ(self) -> None:
        cat = make_cat("test")
        cat.mount("sense", "ears", object())
        assert cat.has_organ("sense", "ears") is True
        assert cat.has_organ("sense", "eyes") is False

    def test_unmount(self) -> None:
        cat = make_cat("test")
        cat.mount("sense", "ears", object())
        assert cat.unmount("sense", "ears") is True
        assert cat.has_organ("sense", "ears") is False
        assert cat.unmount("sense", "ears") is False  # 再次卸载

    def test_organs_snapshot_is_copy(self) -> None:
        cat = make_cat("test")
        a, b = object(), object()
        cat.mount("brain", "a", a)
        cat.mount("brain", "b", b)
        snap = cat.organs("brain")
        assert snap == {"a": a, "b": b}
        # 修改快照不影响内部
        snap["evil"] = object()
        assert cat.has_organ("brain", "evil") is False

    def test_assert_organs_mounted_passes(self) -> None:
        cat = make_cat("test")
        cat.mount("brain", "a", object())
        cat.assert_organs_mounted([("brain", "a")])  # 不抛

    def test_assert_organs_mounted_raises(self) -> None:
        cat = make_cat("test")
        with pytest.raises(OrganNotMountedError):
            cat.assert_organs_mounted([("brain", "missing")])


class TestMountProtocolCheck:
    """mount 带 Protocol 校验。"""

    def test_mount_valid_protocol(self) -> None:
        cat = make_cat("test")

        class RealOrgan:
            name = "real"

            def diagnose(self) -> dict:  # type: ignore[type-arg]
                return {}

        cat.mount("brain", "a", RealOrgan(), protocol=OrganProtocol)  # 不抛

    def test_mount_invalid_protocol_raises(self) -> None:
        cat = make_cat("test")

        class FakeOrgan:
            pass  # 没有 name 属性

        with pytest.raises(OrganProtocolMismatchError) as exc:
            cat.mount("brain", "a", FakeOrgan(), protocol=OrganProtocol)
        assert exc.value.category == "brain"
        assert exc.value.name == "a"


# -- CatBase signal（神经突触）--------------------------------------


class TestCatBaseSignal:
    """CatBase.signal 合法/非法/awaitable。"""

    def test_signal_allowed_path(self) -> None:
        import anyio

        cat = make_cat("test")

        class Target:
            def greet(self, name: str) -> str:
                return f"hello {name}"

        # v0.5.11: signal 增加 Protocol 契约校验，
        # 本测试只验证 wiring allowed_path 放行逻辑，故用未映射坐标避免契约误伤
        cat.mount("brain", "cerebrum", object())
        cat.mount("brain", "custom_target", Target())
        cat.wiring.connect(("brain", "cerebrum"), ("brain", "custom_target"))

        async def _run() -> None:
            result = await cat.signal(
                ("brain", "cerebrum"), ("brain", "custom_target"),
                "greet", "world",
            )
            assert result == "hello world"

        anyio.run(_run)

    def test_signal_illegal_path_raises(self) -> None:
        import anyio

        cat = make_cat("test")
        cat.mount("brain", "cerebrum", object())
        cat.mount("sense", "paws", object())
        # cerebrum→paws 不在 wiring 里

        async def _run() -> None:
            with pytest.raises(IllegalNeuralPathError):
                await cat.signal(
                    ("brain", "cerebrum"), ("sense", "paws"), "do_sth",
                )

        anyio.run(_run)

    def test_signal_awaits_coroutine(self) -> None:
        import anyio

        cat = make_cat("test")

        class AsyncTarget:
            async def fetch(self) -> str:
                return "async-result"

        cat.mount("brain", "a", object())
        cat.mount("brain", "b", AsyncTarget())
        cat.wiring.connect(("brain", "a"), ("brain", "b"))

        async def _run() -> None:
            result = await cat.signal(
                ("brain", "a"), ("brain", "b"), "fetch",
            )
            assert result == "async-result"

        anyio.run(_run)

    def test_signal_emits_nerve_event(self) -> None:
        import anyio

        cat = make_cat("test")
        seen: list[dict] = []

        cat.on("nerve.signal", lambda p: seen.append(p))

        class Target:
            def ping(self) -> str:
                return "pong"

        cat.mount("brain", "a", object())
        cat.mount("brain", "b", Target())
        cat.wiring.connect(("brain", "a"), ("brain", "b"))

        async def _run() -> None:
            await cat.signal(("brain", "a"), ("brain", "b"), "ping")

        anyio.run(_run)
        assert len(seen) == 1
        assert seen[0]["method"] == "ping"


# -- CatBase perceive -----------------------------------------------


class TestCatBasePerceive:
    """CatBase.perceive 反射入口。"""

    def test_perceive_no_reflex_raises(self) -> None:
        import anyio

        cat = make_cat("test")

        async def _run() -> None:
            with pytest.raises(NoReflexMatchedError):
                async for _ in cat.perceive("hello"):
                    pass

        anyio.run(_run)

    def test_perceive_with_reflex_no_stages(self) -> None:
        """有 reflex 但无 stages：只沿 path 逐跳广播。"""
        import anyio

        cat = make_cat("test")
        signals: list[dict] = []
        cat.on("nerve.signal", lambda p: signals.append(p))

        cat.wiring.connect(("brain", "a"), ("brain", "b"))
        cat.register_reflex(Reflex(
            name="ping",
            trigger=lambda x: isinstance(x, str),
            path=(("brain", "a"), ("brain", "b")),
        ))
        cat.freeze_nervous_system()

        async def _run() -> None:
            async for _ in cat.perceive("hello"):
                pass

        anyio.run(_run)
        # 应该触发逐跳广播
        assert len(signals) >= 1


# -- CatBase _assemble ----------------------------------------------


class TestCatBaseAssemble:
    """CatBase._assemble 自动装配。"""

    def test_assemble_mounts_brain_organs(self) -> None:
        cat = make_cat("test")

        class FakeCerebrum:
            name = "fake"

            async def generate(self, prompt, system_prompt=None,
                               temperature=0.7, max_tokens=None) -> str:
                return "fake"

            async def stream_generate(self, prompt, system_prompt=None,
                                      temperature=0.7, max_tokens=None):
                yield "fake"

            def reload_config(self) -> None:
                pass

        cat.cerebrum = FakeCerebrum()  # type: ignore[attr-defined]
        cat._assemble()
        assert cat.has_organ("brain", "cerebrum")

    def test_assemble_mounts_sense_organs(self) -> None:
        cat = make_cat("test")

        class FakeEars:
            name = "fake"

            async def hear(self, raw_input):
                return {}

            def extract_keywords(self, text, top_k=5):
                return []

            def detect_language(self, text):
                return "en"

        cat.ears = FakeEars()  # type: ignore[attr-defined]
        cat._assemble()
        assert cat.has_organ("sense", "ears")

    def test_assemble_mounts_voice_organs(self) -> None:
        cat = make_cat("test")

        class FakeMouth:
            name = "fake"

            def diagnose(self) -> dict:  # type: ignore[type-arg]
                return {}

        cat.mouth = FakeMouth()  # type: ignore[attr-defined]
        cat._assemble()
        assert cat.has_organ("voice", "mouth")

    def test_assemble_freezes_wiring(self) -> None:
        cat = make_cat("test")
        cat._assemble()
        assert cat.wiring.frozen is True

    def test_assemble_registers_text_dialogue_reflex(self) -> None:
        cat = make_cat("test")
        ref = Reflex(
            name="text_dialogue",
            trigger=lambda x: True,
            path=(("sense", "ears"), ("brain", "thalamus")),
        )
        cat._assemble(reflexes=[ref])
        reflex = cat.reflexes.get("text_dialogue")
        assert reflex is not None
        assert reflex.name == "text_dialogue"


# -- CatBase 权限控制 (v1.0.1) ---------------------------------------


class TestCatBaseForbiddenMethods:
    """CatBase.forbidden_methods 黑名单（替代 KittenBase）。"""

    def test_cat_with_forbidden_methods(self) -> None:
        import anyio

        cat = make_cat(
            "k1",
            forbidden_methods=frozenset({"spawn_kitten", "absorb_merge"}),
        )
        cat.mount("brain", "a", object())
        cat.mount("brain", "b", object())
        cat.wiring.connect(("brain", "a"), ("brain", "b"))

        async def _run() -> None:
            with pytest.raises(IllegalNeuralPathError) as exc:
                await cat.signal(
                    ("brain", "a"), ("brain", "b"), "spawn_kitten",
                )
            assert "spawn_kitten" in str(exc.value)

        anyio.run(_run)

    def test_cat_forbidden_absorb_merge(self) -> None:
        import anyio

        cat = make_cat(
            "k1",
            forbidden_methods=frozenset({"spawn_kitten", "absorb_merge"}),
        )
        cat.mount("brain", "a", object())
        cat.mount("brain", "b", object())
        cat.wiring.connect(("brain", "a"), ("brain", "b"))

        async def _run() -> None:
            with pytest.raises(IllegalNeuralPathError):
                await cat.signal(
                    ("brain", "a"), ("brain", "b"), "absorb_merge",
                )

        anyio.run(_run)

    def test_default_cat_no_forbidden_methods(self) -> None:
        """默认 CatBase（不传 forbidden_methods）方法调用不受限。"""
        cat = make_cat("k1")
        cat.mount("brain", "a", object())
        cat.mount("brain", "b", object())
        cat.wiring.connect(("brain", "a"), ("brain", "b"))
        # 不传 forbidden_methods 时 wiring 正常
        assert cat.wiring.is_allowed(("brain", "a"), ("brain", "b"))
