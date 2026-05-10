# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat 独立测试配置 — 零 meowagent 依赖。

提供常用 fixtures 以减少测试文件中的重复样板代码。
"""

import pytest

from meowcat.colony import Colony
from meowcat.defaults.stores import InMemorySharedStore
from meowcat.testing import make_cat, make_test_colony  # noqa: F401


# ━━ pytest 配置 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def pytest_configure(config: pytest.Config) -> None:
    """注册 meowcat 专用标记。"""
    config.addinivalue_line("markers", "slow: marks tests as slow (durations > 100ms)")
    config.addinivalue_line("markers", "integration: marks tests that require external services")
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
