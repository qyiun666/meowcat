# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat 独立测试配置 — 零 meowagent 依赖。

提供常用 fixtures 和共享 helper 类/函数以减少测试文件中的重复样板代码。
"""

from typing import Any

import pytest

from meowcat.assembly import CatBase
from meowcat.colony import Colony
from meowcat.defaults.stores import InMemorySharedStore
from meowcat.testing import make_cat, make_test_colony  # noqa: F401


# ━━ pytest 配置 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def pytest_configure(config: pytest.Config) -> None:
    """注册 meowcat 专用标记。"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (durations > 100ms)")
    config.addinivalue_line(
        "markers", "integration: marks tests that require external services")
    config.addinivalue_line("markers", "unit: marks fast, isolated unit tests")


# ━━ 基础 Fixtures ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.fixture
def cat_base():
    """最小 CatBase 实例（带测试容器），适配 v1.1.3 强制归属。

    创建一只独立的猫，有独立的 Colony。适合不需要访问 Colony 上下文的测试。
    """
    return make_cat()


@pytest.fixture
def colony():
    """新建隔离的测试 Colony，使用 InMemorySharedStore。

    每个测试函数获得一个全新的 Colony 实例，确保测试间隔离。
    适合需要 Colony 级别操作（如多猫协调、看板读写）的测试。
    """
    return Colony("test", storage=InMemorySharedStore())


@pytest.fixture
def cat_in_colony(colony):
    """在测试 Colony 中创建的默认 CatBase 实例。

    依赖 ``colony`` fixture，猫通过 ``colony.create_cat()`` 注册。
    适合既需要猫又需要访问 Colony 上下文的测试。
    """
    return colony.create_cat(name="test-cat")


# ━━ 共享 Helper 类 / 函数 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class DummyOrgan:
    """跨文件共享的最小信号测试器官（带调用追踪）。

    所有信号测试 / EventBus 并发测试 / Gateway 集成测试使用同一份实现。
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def echo(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(("echo", args, kwargs))
        return {"args": args, "kwargs": kwargs}

    async def async_echo(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(("async_echo", args, kwargs))
        return {"args": args, "kwargs": kwargs}

    def fail(self) -> None:
        raise ValueError("intentional organ failure")

    async def async_fail(self) -> None:
        raise RuntimeError("intentional async organ failure")


class SimpleCerebrum:
    """跨文件共享的最小 cerebrum（返回固定响应）。

    Gateway 集成测试和 do_task E2E 测试使用同一份实现。
    """

    name = "simple"

    async def generate(self, prompt, system_prompt=None, temperature=0.7, max_tokens=None):
        self.last_prompt = prompt  # type: ignore[attr-defined]
        return self._response  # type: ignore[attr-defined]

    async def stream_generate(self, prompt, system_prompt=None, temperature=0.7, max_tokens=None):
        yield self._response  # type: ignore[attr-defined]

    def reload_config(self):
        pass


class MultiStepCerebrum:
    """跨文件共享的多步 cerebrum（每轮返回不同响应）。

    do_task E2E 和其他多轮测试使用同一份实现。
    """

    name = "multi"

    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.call_idx = 0

    async def generate(self, prompt, system_prompt=None, temperature=0.7, max_tokens=None):
        idx = self.call_idx
        self.call_idx += 1
        if idx < len(self.responses):
            return self.responses[idx]
        return "default response"

    async def stream_generate(self, prompt, system_prompt=None, temperature=0.7, max_tokens=None):
        idx = self.call_idx
        self.call_idx += 1
        if idx < len(self.responses):
            yield self.responses[idx]
        else:
            yield "default response"

    def reload_config(self):
        pass


class FakeToolHandler:
    """跨文件共享的调用计数工具 handler。"""

    def __init__(self, result: dict | None = None) -> None:
        self.result = result or {"output": "done"}
        self.calls: list[dict] = []

    def __call__(self, **kw: Any) -> dict:
        self.calls.append(kw)
        return self.result


def make_colony(*cats: tuple[str, str], allow_all: bool = False) -> Colony:
    """跨文件共享：创建带已注册猫的 Colony。

    ``cats``: ``(name, uid_hint)`` 元组。
    ``allow_all``: 若为 True，允许所有猫之间的 cross-wiring。
    """
    colony = Colony("test", storage=InMemorySharedStore())
    cat_objs = []
    for name, _ in cats:
        c = colony.create_cat(name=name)
        c.mount("brain", "hippocampus", DummyOrgan())
        cat_objs.append(c)
    if allow_all:
        for a in cat_objs:
            for b in cat_objs:
                if a is not b:
                    colony.allow_cross(a.cat_uid, b.cat_uid)
    return colony
