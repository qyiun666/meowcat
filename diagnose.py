"""meowcat 听诊器 — 全身体检工具。

遍历所有已 mount 器官，调用 ``diagnose()`` 汇总快照。
只依赖 :class:`OrganHost` + :class:`Diagnosable` 协议，零 meowagent import。

用法::

    from meowcat.diagnose import Stethoscope

    health = await Stethoscope.probe_all(cat)
    brain = await Stethoscope.probe_category(cat, "brain")
    hippo = await Stethoscope.probe_organ(cat, "brain", "hippocampus")
"""

from __future__ import annotations

from typing import Any

from meowcat.host import OrganHost
from meowcat.wiring import Edge, Organ, Wiring


def render_wiring(
    wiring: Wiring,
    format: str = "mermaid",
    *,
    organs: frozenset[Organ] | None = None,
) -> str:
    """生成 wiring 图的可视化表示。

    Args:
        wiring: Wiring 实例
        format: 输出格式，``"mermaid"`` 或 ``"dot"``
        organs: 已知器官集合，用于标出孤立节点（可选）

    Returns:
        mermaid 或 dot 格式的图描述字符串。
        - 允许边: 实线箭头
        - 禁止边: 红色虚线
        - 孤立节点（若提供 organs）: 灰色

    Raises:
        ValueError: format 不是 ``"mermaid"`` 或 ``"dot"``

    Examples:

        >>> print(render_wiring(cat.wiring))
        >>> print(render_wiring(cat.wiring, format="dot"))
    """
    if format not in ("mermaid", "dot"):
        raise ValueError(
            f"Unknown format '{format}', expected 'mermaid' or 'dot'"
        )

    allowed = wiring.edges()
    forbidden = wiring.forbids()

    # 从边中收集所有节点
    nodes: set[Organ] = set()
    for frm, to in allowed | forbidden:
        nodes.add(frm)
        nodes.add(to)

    # 若有 organs 参数，加入孤立节点
    if organs is not None:
        nodes |= organs

    # 节点 → 短 ID 映射（mermaid / dot 需要合法标识符）
    node_ids: dict[Organ, str] = {}
    for i, organ in enumerate(sorted(nodes)):
        node_ids[organ] = f"n{i}"

    # 孤立节点 = organs 中有但不在任何边中的节点
    connected: set[Organ] = set()
    for frm, to in allowed | forbidden:
        connected.add(frm)
        connected.add(to)
    isolated = nodes - connected if organs is not None else set()

    if format == "mermaid":
        return _render_mermaid(node_ids, allowed, forbidden, isolated)
    return _render_dot(node_ids, allowed, forbidden, isolated)


def _render_mermaid(
    node_ids: dict[Organ, str],
    allowed: frozenset[Edge],
    forbidden: frozenset[Edge],
    isolated: set[Organ],
) -> str:
    lines = ["graph LR"]

    # 节点声明
    for organ, nid in sorted(node_ids.items(), key=lambda x: x[1]):
        label = f"{organ[0]}:{organ[1]}"
        lines.append(f"    {nid}(\"{label}\")")

    # 允许边
    for i, (frm, to) in enumerate(sorted(allowed)):
        lines.append(f"    {node_ids[frm]} --> {node_ids[to]}")

    # 禁止边
    for i, (frm, to) in enumerate(sorted(forbidden)):
        lines.append(f"    {node_ids[frm]} -.->|✗| {node_ids[to]}")

    # 孤立节点样式
    for organ in sorted(isolated):
        lines.append(f"    style {node_ids[organ]} fill:#ddd,stroke:#999")

    return "\n".join(lines)


def _render_dot(
    node_ids: dict[Organ, str],
    allowed: frozenset[Edge],
    forbidden: frozenset[Edge],
    isolated: set[Organ],
) -> str:
    lines = ["digraph Wiring {", "    rankdir=LR;"]

    # 节点声明
    for organ, nid in sorted(node_ids.items(), key=lambda x: x[1]):
        label = f"{organ[0]}:{organ[1]}"
        # 孤立节点灰色
        if organ in isolated:
            lines.append(
                f'    {nid} [label="{label}", style=filled, fillcolor="#ddd"];'
            )
        else:
            lines.append(f'    {nid} [label="{label}"];')

    # 允许边
    for frm, to in sorted(allowed):
        lines.append(f"    {node_ids[frm]} -> {node_ids[to]};")

    # 禁止边
    for frm, to in sorted(forbidden):
        lines.append(
            f'    {node_ids[frm]} -> {node_ids[to]} '
            f'[color=red, style=dashed, label="✗"];'
        )

    lines.append("}")
    return "\n".join(lines)


class Stethoscope:
    """全身体检工具 — 遍历所有已 mount 器官，调用 diagnose() 汇总。"""

    @staticmethod
    async def probe_all(cat) -> dict[str, dict[str, Any]]:
        """遍历所有已 mount 器官，返回 ``{organ_key: diagnose_snapshot}``。

        Args:
            cat: ``CatBase`` 或拥有 ``_host`` 属性的实例

        Returns:
            ``{"brain:hippocampus": {...}, "sense:ears": {...}, ...}``
            诊断失败的器官对应 ``{"error": str(exc)}``
        """
        host: OrganHost = cat._host
        result: dict[str, dict[str, Any]] = {}
        for category, name in host.list_all_organs():
            key = f"{category}:{name}"
            try:
                result[key] = await cat.probe((category, name))
            except Exception as e:
                result[key] = {"error": str(e)}
        return result

    @staticmethod
    async def probe_category(cat, category: str) -> dict[str, dict[str, Any]]:
        """按分类听诊：只查 ``brain`` / ``sense`` / ``voice`` / ``growth``。

        Args:
            cat: ``CatBase`` 实例
            category: 器官分类名

        Returns:
            ``{"hippocampus": {...}, "cerebrum": {...}}``（省略分类前缀）
        """
        host: OrganHost = cat._host
        result: dict[str, dict[str, Any]] = {}
        for cat_name, instance in host.organs(category).items():
            key = cat_name  # 省略分类前缀
            try:
                result[key] = await cat.probe((category, cat_name))
            except Exception as e:
                result[key] = {"error": str(e)}
        return result

    @staticmethod
    async def probe_organ(cat, category: str, name: str) -> dict[str, Any]:
        """听诊单个器官。

        Args:
            cat: ``CatBase`` 实例
            category: 器官分类名
            name: 器官名

        Returns:
            单个器官的 ``diagnose()`` dict 快照
        """
        return await cat.probe((category, name))


__all__ = ["Stethoscope", "render_wiring"]
