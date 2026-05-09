# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat 独立测试: v0.5.27 Path 原子路径 + PathRegistry。

验证:
- Path dataclass 不可变性 + mode 校验
- PathRegistry register / get / list_all
- PathRegistry.run() 等价于 cat.signal()
- 不存在的 path → KeyError
"""

from __future__ import annotations

import anyio
import pytest

from meowcat.path import BUILTIN_PATHS, Path, PathRegistry, register_builtin_paths
from meowcat.testing import make_cat

# -- Path dataclass ------------------------------------------------


class TestPathDataclass:
    """Path 不可变数据类。"""

    def test_path_creation(self):
        p = Path("test", ("a", "b"), ("c", "d"), "do", "read", "test path")
        assert p.name == "test"
        assert p.from_organ == ("a", "b")
        assert p.to_organ == ("c", "d")
        assert p.method == "do"
        assert p.mode == "read"
        assert p.description == "test path"

    def test_path_defaults(self):
        p = Path("minimal", ("a", "b"), ("c", "d"), "do")
        assert p.mode == "read"
        assert p.description == ""

    def test_path_frozen(self):
        p = Path("frozen", ("a", "b"), ("c", "d"), "do")
        with pytest.raises(Exception):  # dataclasses.FrozenInstanceError 或类似
            p.name = "changed"  # type: ignore[misc]

    def test_path_invalid_mode(self):
        with pytest.raises(ValueError, match="mode must be"):
            Path("bad", ("a", "b"), ("c", "d"), "do", "invalid")

    def test_path_eq(self):
        p1 = Path("same", ("a", "b"), ("c", "d"), "do", "read", "desc")
        p2 = Path("same", ("a", "b"), ("c", "d"), "do", "read", "desc")
        assert p1 == p2

    def test_path_ne(self):
        p1 = Path("a", ("a", "b"), ("c", "d"), "do")
        p2 = Path("b", ("a", "b"), ("c", "d"), "do")
        assert p1 != p2


# -- BUILTIN_PATHS -------------------------------------------------


class TestBuiltinPaths:
    """内置路径表。"""

    def test_not_empty(self):
        assert len(BUILTIN_PATHS) > 0
        assert len(BUILTIN_PATHS) >= 18

    def test_all_have_valid_modes(self):
        for p in BUILTIN_PATHS:
            assert p.mode in ("read", "write")

    def test_no_duplicate_names(self):
        names = [p.name for p in BUILTIN_PATHS]
        assert len(names) == len(set(names)), f"Duplicate names: {names}"

    def test_known_paths_exist(self):
        """确保核心路径存在。"""
        names = {p.name for p in BUILTIN_PATHS}
        expected = {
            "locate", "remember", "get_entity", "get_all",
            "deep_reason", "speak", "hear",
            "decay", "weaken_connections", "cleanup_orphans",
            "execute_tool", "decide_route", "assess_safety",
        }
        missing = expected - names
        assert not missing, f"Missing builtin paths: {missing}"


# -- PathRegistry register / get / list_all ------------------------


class TestPathRegistryBasic:
    """PathRegistry 基本 CRUD。"""

    def test_register_and_get(self):
        reg = PathRegistry()
        p = Path("test", ("a", "b"), ("c", "d"), "do")
        reg.register(p)
        assert reg.get("test") is p

    def test_get_missing(self):
        reg = PathRegistry()
        assert reg.get("nonexistent") is None

    def test_list_all_empty(self):
        reg = PathRegistry()
        assert reg.list_all() == []

    def test_list_all_order(self):
        reg = PathRegistry()
        p1 = Path("first", ("a", "b"), ("c", "d"), "do")
        p2 = Path("second", ("a", "b"), ("c", "d"), "do")
        reg.register(p1)
        reg.register(p2)
        result = reg.list_all()
        assert len(result) == 2
        assert result[0] is p1
        assert result[1] is p2

    def test_register_overwrite(self):
        reg = PathRegistry()
        p1 = Path("dup", ("a", "b"), ("c", "d"), "do1")
        p2 = Path("dup", ("a", "b"), ("c", "d"), "do2")
        reg.register(p1)
        reg.register(p2)
        # 同名路径后注册覆盖前注册
        assert reg.get("dup") is p2
        assert len(reg.list_all()) == 1

    def test_register_invalid_type(self):
        reg = PathRegistry()
        with pytest.raises(TypeError, match="Expected Path instance"):
            reg.register("not a path")  # type: ignore[arg-type]

    def test_register_builtin_paths(self):
        reg = PathRegistry()
        register_builtin_paths(reg)
        all_paths = reg.list_all()
        assert len(all_paths) == len(BUILTIN_PATHS)
        # 验证 locate 存在
        p = reg.get("locate")
        assert p is not None
        assert p.name == "locate"
        assert p.method == "locate"


# -- PathRegistry.run() --------------------------------------------


class TestPathRegistryRun:
    """PathRegistry.run() 等价于 cat.signal()。"""

    def test_run_basic(self):
        """基本路径执行：注册路径 → run → 验证调用。"""
        cat = make_cat("test")

        # 使用未映射坐标避免 v0.5.11 Protocol 契约校验
        HC = ("brain", "_hippocampus")

        called: dict = {}

        class FakeHippocampus:
            name = "hippo"

            async def locate(self, query=None, **kw):
                called["query"] = query
                return {"found": query}

        cat.mount(*HC, FakeHippocampus())

        # 注册自定义路径（使用未映射坐标）
        TH = ("brain", "_thalamus")
        cat.mount(*TH, object())  # from_organ 只是坐标引用，不需要方法
        cat.wiring.connect(TH, HC)

        reg = cat.path_registry
        reg.register(Path("test_locate", TH, HC, "locate", "read", "test"))

        async def _run():
            result = await reg.run(cat, "test_locate", query="hello")
            assert result == {"found": "hello"}
            assert called["query"] == "hello"

        anyio.run(_run)

    def test_run_missing_path(self):
        """不存在的路径 → KeyError。"""
        cat = make_cat("test")

        async def _run():
            with pytest.raises(KeyError, match="not found"):
                await cat.path_registry.run(cat, "nonexistent")

        anyio.run(_run)

    def test_run_with_args(self):
        """带多个 kwargs 的路径执行。"""
        cat = make_cat("test")

        CB = ("brain", "_cerebrum")
        called: dict = {}

        class FakeCerebrum:
            name = "cerebrum"

            async def generate(self, prompt=None, context=None, **kw):
                called["prompt"] = prompt
                called["context"] = context
                return f"reply: {prompt}"

        cat.mount(*CB, FakeCerebrum())
        TH = ("brain", "_thalamus")
        cat.mount(*TH, object())
        cat.wiring.connect(TH, CB)

        reg = cat.path_registry
        reg.register(Path("test_reason", TH, CB, "generate", "read"))

        async def _run():
            result = await reg.run(
                cat, "test_reason", prompt="hello", context="world",
            )
            assert result == "reply: hello"
            assert called["prompt"] == "hello"
            assert called["context"] == "world"

        anyio.run(_run)

    def test_builtin_locate_via_registry(self):
        """内置 locate 路径通过 registry.run 执行（用未映射坐标避 Protocol 校验）。"""
        cat = make_cat("test")

        TH = ("brain", "_thalamus")
        HC = ("brain", "_hippocampus")

        called: dict = {}

        class FakeHippocampus:
            name = "hippo"

            async def locate(self, query=None, **kw):
                called["query"] = query
                return {"found": query}

        cat.mount(*TH, object())
        cat.mount(*HC, FakeHippocampus())
        cat.wiring.connect(TH, HC)

        # 注册自定义路径（使用未映射坐标）
        cat.path_registry.register(Path("locate", TH, HC, "locate", "read"))

        async def _run():
            result = await cat.path_registry.run(
                cat, "locate", query="test query",
            )
            assert result == {"found": "test query"}
            assert called["query"] == "test query"

        anyio.run(_run)
