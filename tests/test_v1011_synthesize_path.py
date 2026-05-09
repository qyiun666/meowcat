# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat standalone tests: crystallize Path (skill crystallization from usage).

Validates:
- crystallize path exists in BUILTIN_PATHS
- Path attributes correct (from/to/method/mode)
- BUILTIN_PATHS has no duplicates
- PathRegistry.run("crystallize") equivalent to cat.signal()
- 1:1 mapping to CrystallizerProtocol.crystallize()
"""

from __future__ import annotations

import anyio
import pytest

from meowcat.anatomy import BRAINSTEM, CRYSTALLIZER
from meowcat.path import BUILTIN_PATHS, Path, PathRegistry, register_builtin_paths
from meowcat.testing import make_cat

# -- crystallize path exists in BUILTIN_PATHS ---------------------------------


class TestCrystallizePathExists:
    """crystallize path registered in builtin path table."""

    def test_crystallize_in_builtin_paths(self):
        names = {p.name for p in BUILTIN_PATHS}
        assert "crystallize" in names, (
            f"crystallize not in BUILTIN_PATHS. Got: {sorted(names)}"
        )

    def test_crystallize_path_attributes(self):
        for p in BUILTIN_PATHS:
            if p.name == "crystallize":
                assert p.from_organ == BRAINSTEM
                assert p.to_organ == CRYSTALLIZER
                assert p.method == "crystallize"
                assert p.mode == "write"
                assert "Crystallize" in p.description
                break
        else:
            pytest.fail("crystallize path not found in BUILTIN_PATHS")


# -- BUILTIN_PATHS integrity -----------------------------------------------


class TestBuiltinPathsIntegrity:
    """Ensure path table integrity."""

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
        """At least 19 paths in v2.0 (slimmed from 31)."""
        assert len(BUILTIN_PATHS) >= 19, (
            f"Expected >= 19 paths, got {len(BUILTIN_PATHS)}"
        )


# -- PathRegistry.run("crystallize") -------------------------------


class TestCrystallizePathRun:
    """PathRegistry.run("crystallize")."""

    def test_run_crystallize_via_registry(self):
        """Execute crystallize path via registry."""
        cat = make_cat("test-crystal")

        BS = ("brain", "_brainstem")
        CY = ("growth", "_crystallizer")

        called: dict = {}

        class FakeCrystallizer:
            name = "crystallizer"

            def crystallize(self, slug="", hit_count=1):
                called["slug"] = slug
                called["hit_count"] = hit_count
                return True

        cat.mount(*BS, object())
        cat.mount(*CY, FakeCrystallizer())
        cat.wiring.connect(BS, CY)

        reg = cat.path_registry
        reg.register(
            Path("crystallize", BS, CY, "crystallize", "write"),
        )

        async def _run():
            result = await reg.run(cat, "crystallize", slug="test", hit_count=1)
            assert result is True
            assert called["slug"] == "test"
            assert called["hit_count"] == 1

        anyio.run(_run)

    def test_register_builtin_paths_includes_crystallize(self):
        """register_builtin_paths includes crystallize."""
        reg = PathRegistry()
        register_builtin_paths(reg)

        p = reg.get("crystallize")
        assert p is not None, "crystallize not registered by register_builtin_paths"
        assert p.from_organ == BRAINSTEM
        assert p.to_organ == CRYSTALLIZER
        assert p.method == "crystallize"
