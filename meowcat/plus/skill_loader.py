# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat plus SKILL.md Loader — discover and load skills from SKILL.md files.

Scans directories for SKILL.md files, parses YAML frontmatter, creates
Tool objects registerable into any ``ToolRegistry``.

Usage::

    loader = SkillLoader(skills_dir=Path("./skills"))
    tools = loader.scan_directory()
    loader.register_all(cat.tool_registry)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from meowcat.tools.tool import RiskLevel, Tool, ToolRegistry, ToolSpec

logger = logging.getLogger(__name__)

_RISK_MAP = {"low": RiskLevel.LOW,
             "medium": RiskLevel.MEDIUM, "high": RiskLevel.HIGH}


def _parse_frontmatter(text: str) -> dict[str, Any]:
    """Parse simple YAML frontmatter: key: value, nested dicts, lists, inline dicts."""
    result: dict[str, Any] = {}
    key: str | None = None
    indent_stack: list[int] = [0]
    ctx_stack: list[dict[str, Any]] = [result]

    for line in text.strip().split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())

        # Pop back to matching indent level
        while len(indent_stack) > 1 and indent <= indent_stack[-2]:
            indent_stack.pop()
            ctx_stack.pop()

        if stripped.startswith("- ") and key is not None:
            # List item under current key
            val = _parse_scalar(stripped[2:].strip())
            cur = ctx_stack[-1]
            if key not in cur or not isinstance(cur[key], list):
                cur[key] = []
            cur[key].append(val)
            continue

        if ":" not in stripped:
            continue

        k, _, v = stripped.partition(":")
        k = k.strip()
        v = v.strip()

        if v:
            ctx_stack[-1][k] = _parse_scalar(v)
            key = k
        else:
            # Nested dict — push context on next indented line
            ctx_stack[-1][k] = {}
            key = k
            indent_stack.append(indent)
            ctx_stack.append(ctx_stack[-1][k])

    return result


def _parse_scalar(val: str) -> Any:
    """Parse scalar: bool, int, float, inline dict/list, or string."""
    if val.startswith("{") and val.endswith("}"):
        inner = val[1:-1].strip()
        d: dict[str, str] = {}
        for item in _split_csv(inner):
            if ":" in item:
                ik, iv = item.split(":", 1)
                d[ik.strip()] = iv.strip().strip("'\"")
        return d
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        return [x.strip().strip("'\"") for x in _split_csv(inner)] if inner else []
    vl = val.lower()
    if vl in ("true", "false"):
        return vl == "true"
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val.strip("'\"")


def _split_csv(text: str) -> list[str]:
    """Split comma-separated values, respecting quotes."""
    items: list[str] = []
    buf: list[str] = []
    in_q: str | None = None
    for ch in text:
        if ch in ("'", '"'):
            if in_q == ch:
                in_q = None
            elif in_q is None:
                in_q = ch
            buf.append(ch)
        elif ch == "," and in_q is None:
            items.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf:
        items.append("".join(buf).strip())
    return items


class SkillLoader:
    """SKILL.md file loader — scans directories and converts SKILL.md to Tools.

    Each SKILL.md is parsed for YAML frontmatter (``---`` delimited) to extract
    name, description, parameters, risk, and category. The markdown body is
    preserved as the tool's execution output.

    Usage::

        loader = SkillLoader(skills_dir=Path("./skills"))
        tools = loader.scan_directory()
        n = loader.register_all(cat.tool_registry)  # returns count
    """

    def __init__(self, skills_dir: Path) -> None:
        self.skills_dir = Path(skills_dir)
        self._tools: list[Tool] = []

    def scan_directory(self) -> list[Tool]:
        """Recursively scan ``skills_dir`` for ``SKILL.md`` files.

        Returns:
            List of :class:`Tool` objects created from discovered SKILL.md files.
        """
        self._tools.clear()
        if not self.skills_dir.is_dir():
            logger.warning("Skills directory not found: %s", self.skills_dir)
            return []

        for skill_file in sorted(self.skills_dir.rglob("SKILL.md")):
            try:
                tool = self._load_skill(skill_file)
                if tool is not None:
                    self._tools.append(tool)
                    logger.debug("Loaded skill: %s from %s",
                                 tool.name, skill_file)
            except Exception as exc:
                logger.warning("Failed to load %s: %s", skill_file, exc)
        return list(self._tools)

    def _load_skill(self, path: Path) -> Tool | None:
        """Parse a single SKILL.md into a Tool."""
        content = path.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        if len(parts) < 3:
            logger.warning("No frontmatter in %s", path)
            return None

        meta = _parse_frontmatter(parts[1])
        body = parts[2].strip()

        name = str(meta.get("name", path.parent.name))
        description = str(meta.get("description", ""))

        params: dict[str, dict[str, str]] = {}
        raw_params = meta.get("parameters", {})
        if isinstance(raw_params, dict):
            for pk, pv in raw_params.items():
                if isinstance(pv, dict):
                    params[str(pk)] = {str(k): str(v) for k, v in pv.items()}
                else:
                    params[str(pk)] = {"type": "string",
                                       "description": str(pv)}
        elif isinstance(raw_params, list):
            params = {str(p): {} for p in raw_params}

        risk_str = str(meta.get("risk", "medium")).lower()
        risk = _RISK_MAP.get(risk_str, RiskLevel.MEDIUM)
        category = str(meta.get("category", "skill"))

        spec = ToolSpec(
            name=name,
            description=description,
            parameters=params,
            risk=risk,
            category=category,
        )

        # Capture body in closure — each tool returns its SKILL.md body
        _body = body

        async def _handler(**_: Any) -> str:
            return _body

        return Tool(spec, handler=_handler)

    def register_all(self, registry: ToolRegistry) -> int:
        """Register all loaded tools into *registry*. Returns count registered."""
        for tool in self._tools:
            registry.register(tool)
        return len(self._tools)

