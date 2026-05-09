# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""
v1.0.3 — Wiring 可视化测试
=============================

验证:
    1. TestRenderWiring    — render_wiring 函数 (mermaid / dot / 边界)
    2. TestWiringDiagram   — CatBase.wiring_diagram() 快捷方法
"""

from __future__ import annotations

import pytest

from meowcat.assembly import CatBase
from meowcat.diagnose import render_wiring
from meowcat.testing import make_cat
from meowcat.wiring import Wiring

# -- 辅助 ---------------------------------------------------------

def _make_wired_cat() -> CatBase:
    """创建一个带简单 wiring 的猫。"""
    cat = make_cat("test-cat")
    cat.wire_default_nervous_system()
    return cat


# -- 1. render_wiring 函数 -----------------------------------------

class TestRenderWiring:
    """render_wiring() 函数各种场景。"""

    def test_empty_wiring_mermaid(self) -> None:
        """空 wiring → 有效的 mermaid。"""
        w = Wiring()
        result = render_wiring(w)
        assert result.startswith("graph LR")
        # 空图: 没有节点声明（无器官参数）
        lines = result.strip().split("\n")
        assert lines[0] == "graph LR"

    def test_empty_wiring_dot(self) -> None:
        """空 wiring → 有效的 dot。"""
        w = Wiring()
        result = render_wiring(w, format="dot")
        assert "digraph Wiring {" in result
        assert result.strip().endswith("}")

    def test_wiring_with_edges_mermaid(self) -> None:
        """有允许边的 wiring → mermaid 含节点和边。"""
        w = Wiring()
        w.connect(("brain", "cerebrum"), ("brain", "hippocampus"))
        w.connect(("brain", "thalamus"), ("brain", "cerebrum"))
        result = render_wiring(w)
        lines = result.strip().split("\n")
        assert lines[0] == "graph LR"
        # 应包含三个节点的声明和两条边
        assert any("n0" in line or "n1" in line for line in lines)
        assert sum(1 for line in lines if "-->" in line) == 2

    def test_wiring_with_edges_dot(self) -> None:
        """有允许边的 wiring → dot 含节点和边。"""
        w = Wiring()
        w.connect(("brain", "cerebrum"), ("brain", "hippocampus"))
        result = render_wiring(w, format="dot")
        assert "digraph Wiring {" in result
        assert "->" in result
        assert result.strip().endswith("}")

    def test_wiring_with_forbidden_edges_mermaid(self) -> None:
        """含禁止边的 wiring → mermaid 显示虚线。"""
        w = Wiring()
        w.connect(("brain", "cerebellum"), ("sense", "paws"))
        w.forbid(("brain", "cerebrum"), ("sense", "paws"))
        result = render_wiring(w)
        # 禁止边用 -.-> 标记
        assert "-.->" in result
        assert "✗" in result
        # 允许边用 -->
        assert "-->" in result

    def test_wiring_with_forbidden_edges_dot(self) -> None:
        """含禁止边的 wiring → dot 显示红色虚线。"""
        w = Wiring()
        w.connect(("brain", "cerebellum"), ("sense", "paws"))
        w.forbid(("brain", "cerebrum"), ("sense", "paws"))
        result = render_wiring(w, format="dot")
        assert "color=red" in result
        assert "style=dashed" in result

    def test_invalid_format(self) -> None:
        """不支持的格式抛出 ValueError。"""
        w = Wiring()
        with pytest.raises(ValueError, match="Unknown format"):
            render_wiring(w, format="svg")

    def test_with_organs_isolated_nodes(self) -> None:
        """提供 organs 参数时孤立节点标记为灰色。"""
        w = Wiring()
        w.connect(("brain", "cerebrum"), ("brain", "hippocampus"))
        # ("sense", "whiskers") 不在任何边中 → 孤立节点
        organs = frozenset({
            ("brain", "cerebrum"),
            ("brain", "hippocampus"),
            ("sense", "whiskers"),
        })
        result = render_wiring(w, organs=organs)
        # 孤立节点应有灰色样式
        assert "fill:#ddd" in result

    def test_with_organs_isolated_nodes_dot(self) -> None:
        """dot 格式的孤立节点标记为灰色。"""
        w = Wiring()
        w.connect(("brain", "cerebrum"), ("brain", "hippocampus"))
        organs = frozenset({
            ("brain", "cerebrum"),
            ("brain", "hippocampus"),
            ("sense", "whiskers"),
        })
        result = render_wiring(w, format="dot", organs=organs)
        assert 'fillcolor="#ddd"' in result


# -- 2. CatBase.wiring_diagram() 快捷方法 --------------------------

class TestWiringDiagram:
    """CatBase.wiring_diagram() 方法。"""

    def test_default_format(self) -> None:
        """默认返回 mermaid 格式。"""
        cat = make_cat("test")
        cat.mount("brain", "hippocampus", object())
        cat.wire_default_nervous_system()
        result = cat.wiring_diagram()
        assert result.startswith("graph LR")
        assert "-->" in result or "-.->" in result

    def test_dot_format(self) -> None:
        """format='dot' 返回 dot 格式。"""
        cat = make_cat("test")
        cat.mount("brain", "hippocampus", object())
        cat.wire_default_nervous_system()
        result = cat.wiring_diagram(format="dot")
        assert "digraph Wiring {" in result
        assert "}" in result

    def test_wiring_disabled_raises(self) -> None:
        """wiring 禁用时抛 AttributeError。"""
        cat = make_cat("test", enable_wiring=False)
        with pytest.raises(AttributeError, match="wiring disabled"):
            cat.wiring_diagram()

