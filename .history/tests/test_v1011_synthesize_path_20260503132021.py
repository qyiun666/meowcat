"""meowcat 独立测试: v1.0.11 synthesize Path（世界观综合）。

验证:
- synthesize 路径存在于 BUILTIN_PATHS
- 路径属性正确（from/ to / method / mode）
- BUILTIN_PATHS 无重名（含 synthesize 后）
- PathRegistry.run("synthesize") 等价于 cat.signal()
- 1:1 对应 CortexProtocol.synthesize()
"""

from __future__ import annotations

import anyio
import pytest

from meowcat import CatBase
from meowcat.anatomy import BRAINSTEM, CORTEX
from meowcat.path import BUILTIN_PATHS, Path, PathRegistry, register_builtin_paths


# -- synthesize 路径存在于 BUILTIN_PATHS -------------------------


class TestSynthesizePathExists:
    """synthesize 路径已注册到内置路径表。"""

    def test_synthesize_in_builtin_paths(self):
        names = {p.name for p in BUILTIN_PATHS}
        assert "synthesize" in names, (
            f"synthesize not in BUILTIN_PATHS. Got: {sorted(names)}"
        )

    def test_synthesize_path_attributes(self):
        for p in BUILTIN_PATHS:
            if p.name == "synthesize":
                assert p.from_organ == BRAINSTEM
                assert p.to_organ == CORTEX
                assert p.method == "synthesize"
                assert p.mode == "read"
                assert "Worldview synthesis" in p.description
                break
        else:
            pytest.fail("synthesize path not found in BUILTIN_PATHS")


# -- BUILTIN_PATHS 完整性（含 synthesize） ------------------------


class TestBuiltinPathsWithSynthesize:
    """确保新增 synthesize 后路径表仍完整。"""

    def test_no_duplicate_names(self):
        names = [p.name for p in BUILTIN_PATHS]
        assert len(names) == len(set(names)), (
            f"Duplicate names in BUILTIN_PATHS: {names}"
        )

    def test_all_have_valid_modes(self):
        for p in BUILTIN_PATHS:
            assert p.mode in ("read", "write"), (
                f"Path {p.name} has invalid mode: {p.mode}"
            )

    def test_minimum_path_count(self):
        """v1.0.11 后至少 23 条路径（22 + synthesize = 23）。"""
        assert len(BUILTIN_PATHS) >= 23, (
            f"Expected >= 23 paths, got {len(BUILTIN_PATHS)}"
        )


# -- PathRegistry.run("synthesize") -------------------------------


class TestSynthesizePathRun:
    """PathRegistry.run("synthesize") 等价于 cat.signal(BRAINSTEM, CORTEX, "synthesize")。"""

    def test_run_synthesize_via_registry(self):
        """通过 registry 执行 synthesize 路径。"""
        cat = CatBase("test-synth")

        # 使用未映射坐标避 Protocol 校验
        BS = ("brain", "_brainstem")
        CX = ("brain", "_cortex")

        called: dict = {}

        class FakeCortex:
            name = "cortex"

            def synthesize(self, max_tokens=400):
                called["max_tokens"] = max_tokens
                return "worldview: everything is connected"

        cat.mount(*BS, object())
        cat.mount(*CX, FakeCortex())
        cat.wiring.connect(BS, CX)

        reg = cat.path_registry
        reg.register(
            Path("synthesize", BS, CX, "synthesize", "read", "世界观综合"),
        )

        async def _run():
            result = await reg.run(cat, "synthesize", max_tokens=200)
            assert result == "worldview: everything is connected"
            assert called["max_tokens"] == 200

        anyio.run(_run)

    def test_run_synthesize_default_max_tokens(self):
        """synthesize 默认 max_tokens=400 被正确传递。"""
        cat = CatBase("test-synth-default")

        BS = ("brain", "_brainstem")
        CX = ("brain", "_cortex")

        called: dict = {}

        class FakeCortex:
            name = "cortex"

            def synthesize(self, max_tokens=400):
                called["max_tokens"] = max_tokens
                return "summary"

        cat.mount(*BS, object())
        cat.mount(*CX, FakeCortex())
        cat.wiring.connect(BS, CX)

        reg = cat.path_registry
        reg.register(
            Path("synthesize", BS, CX, "synthesize", "read"),
        )

        async def _run():
            result = await reg.run(cat, "synthesize")
            assert result == "summary"
            assert called["max_tokens"] == 400  # 默认值被保留

        anyio.run(_run)

    def test_register_builtin_paths_includes_synthesize(self):
        """register_builtin_paths 包含 synthesize。"""
        reg = PathRegistry()
        register_builtin_paths(reg)

        p = reg.get("synthesize")
        assert p is not None, "synthesize not registered by register_builtin_paths"
        assert p.from_organ == BRAINSTEM
        assert p.to_organ == CORTEX
        assert p.method == "synthesize"
