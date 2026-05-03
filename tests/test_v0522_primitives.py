"""meowcat 独立测试: v0.5.22 新增原语（Stethoscope / Needle）。

验证:
- Stethoscope.probe_all / probe_category / probe_organ
- CatBase.health_check / brain_check
- Needle.poke / poke_memory / poke_focus / poke_worldview
- Needle 环境变量禁用
"""

from __future__ import annotations

import os
from unittest.mock import patch

import anyio
import pytest

from meowcat import CatBase
from meowcat.diagnose import Stethoscope
from meowcat.errors import OrganNotMountedError
from meowcat.inject import Needle, NeedleDisabledError


# -- 测试用器官 ---------------------------------------------------


class FakeDiagnosableOrgan:
    """实现了 diagnose() 的假器官。"""

    def __init__(self, name: str, status: str = "ok"):
        self.name = name
        self._status = status

    def diagnose(self) -> dict:
        return {"name": self.name, "status": self._status}


class FakeBrokenOrgan:
    """没有 diagnose() 的器官，probe 应抛 TypeError。"""

    name = "broken"


class FakeAsyncOrgan:
    """diagnose() 返回 awaitable 的器官。"""

    name = "async"

    async def diagnose(self) -> dict:
        return {"name": "async", "status": "done"}


# -- Stethoscope --------------------------------------------------


class TestStethoscope:
    """Stethoscope 全身体检 / 分类听诊 / 单体听诊。"""

    @pytest.fixture
    def cat_with_organs(self):
        """构造一只挂了两个脑区和一只耳朵的猫（已 wiring）。"""
        cat = CatBase("test_cat")
        cat.mount("brain", "hippocampus", FakeDiagnosableOrgan("hippo", "ok"))
        cat.mount("brain", "cerebrum", FakeDiagnosableOrgan("cerebrum", "ok"))
        cat.mount("sense", "ears", FakeDiagnosableOrgan("ears", "ok"))
        # v0.5.9+: probe 要求器官在 wiring 中注册
        cat.wiring.connect(("_probe", "_probe"), ("brain", "hippocampus"))
        cat.wiring.connect(("_probe", "_probe"), ("brain", "cerebrum"))
        cat.wiring.connect(("_probe", "_probe"), ("sense", "ears"))
        return cat

    def test_probe_all(self, cat_with_organs):
        async def _run():
            result = await Stethoscope.probe_all(cat_with_organs)
            assert "brain:hippocampus" in result
            assert result["brain:hippocampus"]["status"] == "ok"
            assert "brain:cerebrum" in result
            assert "sense:ears" in result
            assert len(result) == 3

        anyio.run(_run)

    def test_probe_category(self, cat_with_organs):
        async def _run():
            result = await Stethoscope.probe_category(cat_with_organs, "brain")
            # probe_category 省略分类前缀
            assert "hippocampus" in result
            assert "cerebrum" in result
            assert "ears" not in result
            assert len(result) == 2

        anyio.run(_run)

    def test_probe_organ(self, cat_with_organs):
        async def _run():
            result = await Stethoscope.probe_organ(
                cat_with_organs, "brain", "hippocampus")
            assert result["name"] == "hippo"
            assert result["status"] == "ok"

        anyio.run(_run)

    def test_probe_all_with_broken_organ(self):
        """有器官不实现 Diagnosable 时 probe 失败，应捕获为 error。"""
        cat = CatBase("test")
        cat.mount("brain", "good", FakeDiagnosableOrgan("good", "ok"))
        cat.mount("brain", "broken", FakeBrokenOrgan())

        async def _run():
            result = await Stethoscope.probe_all(cat)
            assert "error" in result["brain:broken"]

        anyio.run(_run)

    def test_probe_all_with_async_organ(self):
        """diagnose() 返回 awaitable 的器官（需 wiring）。"""
        cat = CatBase("test")
        cat.mount("brain", "async", FakeAsyncOrgan())
        cat.wiring.connect(("_probe", "_probe"), ("brain", "async"))

        async def _run():
            result = await Stethoscope.probe_all(cat)
            assert result["brain:async"]["status"] == "done"

        anyio.run(_run)

    def test_probe_all_empty_cat(self):
        """空猫的 health_check 返回空 dict。"""
        cat = CatBase("empty")

        async def _run():
            result = await Stethoscope.probe_all(cat)
            assert result == {}
        anyio.run(_run)


# -- CatBase health_check / brain_check ---------------------------


class TestCatBaseHealthCheck:
    """CatBase 上的诊断快捷方法。"""

    def test_health_check(self):
        cat = CatBase("test")
        cat.mount("brain", "hippocampus", FakeDiagnosableOrgan("hippo", "ok"))
        cat.mount("sense", "ears", FakeDiagnosableOrgan("ears", "ok"))
        cat.wiring.connect(("_probe", "_probe"), ("brain", "hippocampus"))
        cat.wiring.connect(("_probe", "_probe"), ("sense", "ears"))

        async def _run():
            result = await cat.health_check()
            assert "brain:hippocampus" in result
            assert "sense:ears" in result
            assert len(result) == 2

        anyio.run(_run)

    def test_brain_check(self):
        cat = CatBase("test")
        cat.mount("brain", "hippocampus", FakeDiagnosableOrgan("hippo", "ok"))
        cat.mount("brain", "cerebrum", FakeDiagnosableOrgan("cerebrum", "ok"))
        cat.mount("sense", "ears", FakeDiagnosableOrgan("ears", "ok"))
        cat.wiring.connect(("_probe", "_probe"), ("brain", "hippocampus"))
        cat.wiring.connect(("_probe", "_probe"), ("brain", "cerebrum"))
        cat.wiring.connect(("_probe", "_probe"), ("sense", "ears"))

        async def _run():
            result = await cat.brain_check()
            assert "hippocampus" in result
            assert "cerebrum" in result
            assert "ears" not in result  # sense 不在 brain
            assert len(result) == 2

        anyio.run(_run)


# -- Needle -------------------------------------------------------


class TestNeedle:
    """Needle 绕过 wiring 注入。"""

    def test_poke_basic(self):
        cat = CatBase("test")

        class Target:
            def greet(self, name: str) -> str:
                return f"hello {name}"

        cat.mount("brain", "target", Target())
        needle = Needle(cat)

        async def _run():
            result = await needle.poke(("brain", "target"), "greet", name="world")
            assert result == "hello world"

        anyio.run(_run)

    def test_poke_async_method(self):
        cat = CatBase("test")

        class AsyncTarget:
            async def fetch(self, key: str) -> str:
                return f"got:{key}"

        cat.mount("brain", "target", AsyncTarget())
        needle = Needle(cat)

        async def _run():
            result = await needle.poke(("brain", "target"), "fetch", key="x")
            assert result == "got:x"

        anyio.run(_run)

    def test_poke_organ_not_mounted(self):
        cat = CatBase("test")
        needle = Needle(cat)

        async def _run():
            with pytest.raises(OrganNotMountedError, match="not mounted"):
                await needle.poke(("brain", "missing"), "anything")

        anyio.run(_run)

    def test_poke_method_not_found(self):
        cat = CatBase("test")
        cat.mount("brain", "target", object())
        needle = Needle(cat)

        async def _run():
            with pytest.raises(AttributeError, match="no method"):
                await needle.poke(("brain", "target"), "nonexistent")

        anyio.run(_run)

    def test_poke_memory(self):
        cat = CatBase("test")
        called: dict = {}

        class FakeHippocampus:
            name = "hippo"

            def add_entity(self, **kwargs):
                called.update(kwargs)
                return "ok"

        cat.mount("brain", "hippocampus", FakeHippocampus())
        needle = Needle(cat)

        async def _run():
            result = await needle.poke_memory(name="Python", type="lang")
            assert result == "ok"
            assert called["name"] == "Python"
            assert called["type"] == "lang"

        anyio.run(_run)

    def test_poke_focus(self):
        cat = CatBase("test")
        called: dict = {}

        class FakeFrontal:
            name = "frontal"

            def update_focus(self, result: str):
                called["topic"] = result
                return "set"

        cat.mount("brain", "frontal", FakeFrontal())
        needle = Needle(cat)

        async def _run():
            result = await needle.poke_focus("debugging")
            assert result == "set"
            assert called["topic"] == "debugging"

        anyio.run(_run)

    def test_poke_worldview(self):
        cat = CatBase("test")
        called: dict = {}

        class FakeCortex:
            name = "cortex"

            def ingest(self, source: str, layer: str, key: str, value):
                called["source"] = source
                called["layer"] = layer
                called["key"] = key
                called["value"] = value
                return "ok"

        cat.mount("brain", "cortex", FakeCortex())
        needle = Needle(cat)

        async def _run():
            result = await needle.poke_worldview("axioms", "cat_is", "good")
            assert result == "ok"
            assert called["source"] == "needle"
            assert called["layer"] == "axioms"
            assert called["key"] == "cat_is"
            assert called["value"] == "good"

        anyio.run(_run)

    def test_needle_disabled_by_env(self):
        with patch.dict(os.environ, {"MEOWCAT_DISABLE_NEEDLE": "1"}):
            cat = CatBase("test")
            with pytest.raises(NeedleDisabledError):
                Needle(cat)

