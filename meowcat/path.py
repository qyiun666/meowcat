# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat atomic paths — Path dataclass + PathRegistry + built-in path table.

A Path is an immutable neural signal recipe: from which organ, to which organ,
call which method. PathRegistry manages all registered paths, providing
name-based lookup and execution.

For external developers::

    from meowcat.path import Path, BUILTIN_PATHS

    # View built-in paths
    for p in BUILTIN_PATHS:
        print(f"{p.name}: {p.from_organ} -> {p.to_organ}.{p.method} [{p.mode}]")

    # Execute via cat
    result = await cat.path_registry.run("locate", query="hello")

This file has zero third-party dependencies and zero meowagent imports.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any

from meowcat.anatomy import (
    AMYGDALA,
    ANOMALY_GROWTH,
    BRAINSTEM,
    CEREBELLUM,
    CEREBRUM,
    CORRECTION_GROWTH,
    CRYSTALLIZER,
    EARS,
    HIPPOCAMPUS,
    HYPOTHALAMUS,
    MOUTH,
    PAWS,
    ROLE_EMERGENCE,
    THALAMUS,
)
from meowcat.errors import IllegalNeuralPathError
from meowcat.wiring import Organ


@dataclass(frozen=True)
class Path:
    """An immutable atomic neural signal recipe.

    Each Path describes one ``cat.signal(from_organ, to_organ, method,
    **kwargs)`` call. Path objects are immutable and can be composed into
    :class:`Loop` (v0.5.28) to form closed loops.

    Attributes:
        name: Unique path name, e.g. ``"locate"``
        from_organ: Signal source organ coordinate
        to_organ: Signal target organ coordinate
        method: Method name to call on the target organ
        mode: ``"read"`` or ``"write"``, marking read/write semantics
        description: Human-readable description
    """

    name: str
    from_organ: Organ
    to_organ: Organ
    method: str
    mode: str = "read"
    description: str = ""

    def __post_init__(self) -> None:
        if self.mode not in ("read", "write"):
            raise ValueError(
                f"mode must be 'read' or 'write', got {self.mode!r}")


# -- Builtin path table ------------------------------------------------------

BUILTIN_PATHS: tuple[Path, ...] = (
    # -- Memory domain --
    Path("locate", THALAMUS, THALAMUS, "locate", "read",
         "Retrieve memories (thalamus self-loop)"),
    Path("remember", BRAINSTEM, HIPPOCAMPUS,
         "remember", "write", "Store memory"),
    Path("append_content", BRAINSTEM, HIPPOCAMPUS,
         "append_content", "write", "Append content"),
    # -- Reasoning domain --
    Path("deep_reason", THALAMUS, CEREBRUM, "generate", "read", "Deep reason"),
    # -- Output domain --
    Path("speak", CEREBELLUM, MOUTH, "speak", "write", "Output reply"),
    Path("hear", EARS, THALAMUS, "hear", "read", "Receive input"),
    # -- Maintenance domain --
    Path("decay", HYPOTHALAMUS, HIPPOCAMPUS, "decay", "write", "Decay memory"),
    Path(
        "cleanup_orphans",
        HYPOTHALAMUS,
        HIPPOCAMPUS,
        "cleanup_orphan_connections",
        "write",
        "Cleanup orphan connections",
    ),
    # -- Tool execution domain --
    Path("execute_tool", CEREBELLUM, PAWS, "execute", "write", "Execute tool"),
    # -- Self-loop paths --
    Path("decide_route", THALAMUS, THALAMUS,
         "decide_route", "read", "Routing decision"),
    Path("assess_safety", AMYGDALA, AMYGDALA,
         "assess_safety", "read", "Safety assessment"),
    # -- Orchestration domain --
    Path("workflow_create", BRAINSTEM, HIPPOCAMPUS,
         "add_entity", "write", "Create workflow"),
    Path(
        "workflow_checkpoint",
        BRAINSTEM,
        HIPPOCAMPUS,
        "append_content",
        "write",
        "Write checkpoint",
    ),
    Path("workflow_resume", BRAINSTEM, HIPPOCAMPUS,
         "get_entity", "read", "Resume workflow"),
    # -- Context compression --
    Path(
        "compress_context",
        BRAINSTEM,
        BRAINSTEM,
        "compress_context",
        "write",
        "Compress conversation context",
    ),
    # -- Growth domain --
    Path("record_anomaly", BRAINSTEM, ANOMALY_GROWTH,
         "record", "write", "Record anomaly pattern"),
    Path(
        "record_correction",
        BRAINSTEM,
        CORRECTION_GROWTH,
        "record",
        "write",
        "Record user correction",
    ),
    Path(
        "crystallize",
        BRAINSTEM,
        CRYSTALLIZER,
        "crystallize",
        "write",
        "Crystallize skill from usage",
    ),
    Path(
        "record_pattern",
        BRAINSTEM,
        ROLE_EMERGENCE,
        "record",
        "write",
        "Record role behavior pattern",
    ),
    # -- Tree domain (v2.0) --
    Path("get_tree", THALAMUS, HIPPOCAMPUS, "get_tree", "read", "Read knowledge tree"),
    Path("search_tree", THALAMUS, HIPPOCAMPUS, "search_tree", "read", "Search tree nodes"),
    Path("query_subtree", THALAMUS, HIPPOCAMPUS, "query_subtree", "read", "Query subtree nodes"),
    Path("build_tree", BRAINSTEM, HIPPOCAMPUS, "build_tree", "write", "Build knowledge tree"),
)


def register_builtin_paths(registry: PathRegistry) -> None:
    """Register builtin paths into a PathRegistry.

    Args:
        registry: PathRegistry instance
    """
    for p in BUILTIN_PATHS:
        registry.register(p)


# -- PathRegistry -------------------------------------------------


@dataclass
class PathRegistry:
    """Path registry — manages Path registration, lookup, and execution.

    Usage::

        registry = PathRegistry()
        register_builtin_paths(registry)

        # Lookup
        path = registry.get("locate")
        all_paths = registry.list_all()

        # Execute
        result = await registry.run(cat, "locate", query="hello")
    """

    _paths: dict[str, Path] = field(default_factory=dict, init=False)
    _paths_list: list[Path] = field(default_factory=list, init=False)

    def register(self, path: Path) -> None:
        """Register a path. Same-named paths overwrite old values.

        Args:
            path: Path instance

        Raises:
            TypeError: path is not a Path instance
        """
        if not isinstance(path, Path):
            raise TypeError(
                f"Expected Path instance, got {type(path).__name__}")
        # Overwrite old value (same-named path: later registration wins)
        if path.name in self._paths:
            self._paths_list.remove(self._paths[path.name])
        self._paths[path.name] = path
        self._paths_list.append(path)

    def get(self, name: str) -> Path | None:
        """Lookup path by name.

        Args:
            name: Path name

        Returns:
            Path object, None if not found
        """
        return self._paths.get(name)

    def list_all(self) -> list[Path]:
        """Return all registered paths in registration order."""
        return list(self._paths_list)

    async def run(self, cat: Any, name: str, **kwargs: Any) -> Any:
        """Execute a path.

        Equivalent to::

            path = registry.get(name)
            cat.signal(path.from_organ, path.to_organ, path.method, **kwargs)

        Args:
            cat: CatBase instance (must support
                ``cat.signal(from, to, method, **kwargs)``)
            name: Path name
            **kwargs: Arguments forwarded to the target method

        Returns:
            Target method return value

        Raises:
            KeyError: Path not found
        """
        path = self.get(name)
        if path is None:
            raise KeyError(f"Path '{name}' not found in registry")

        # Self-loop: from == to, call local method directly
        # (bypass wiring validation; wiring has no self-loop edges)
        if path.from_organ == path.to_organ:
            # v1.2.25: enforce forbidden_methods even on self-loops
            if (
                hasattr(cat, "nervous")
                and cat.nervous is not None
                and path.method in cat.nervous.forbidden_methods
            ):
                raise IllegalNeuralPathError(
                    path.from_organ,
                    path.to_organ,
                    reason=f"forbidden method '{path.method}'",
                )
            organ = cat.organ(*path.to_organ)
            method = getattr(organ, path.method)
            result = method(**kwargs)
            if inspect.isawaitable(result):
                result = await result
            return result

        return await cat.signal(
            path.from_organ,
            path.to_organ,
            path.method,
            **kwargs,
        )


__all__ = ["Path", "PathRegistry", "BUILTIN_PATHS", "register_builtin_paths"]
