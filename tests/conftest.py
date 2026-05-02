"""meowcat 独立测试配置 — 零 meowagent 依赖。"""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """注册 meowcat 专用标记。"""
    config.addinivalue_line("markers", "slow: marks tests as slow")
