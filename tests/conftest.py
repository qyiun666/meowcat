"""meowcat 独立测试配置 — 零 meowagent 依赖。"""

import pytest

from meowcat.testing import make_cat, make_test_colony  # noqa: F401


def pytest_configure(config: pytest.Config) -> None:
    """注册 meowcat 专用标记。"""
    config.addinivalue_line("markers", "slow: marks tests as slow")


@pytest.fixture
def cat_base():
    """最小 CatBase 实例（带测试容器），适配 v1.1.3 强制归属。"""
    return make_cat()
