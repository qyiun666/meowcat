# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat chain — Chain dataclass + ChainRegistry + built-in chain table.

A Chain is a named Path sequence for multi-step operations that don't require
a closed loop. ChainRegistry manages all registered chains, providing
name-based lookup and sequential execution.

For external developers::

    from meowcat.chain import Chain, BUILTIN_CHAINS

    # View built-in chains
    for c in BUILTIN_CHAINS:
        print(f"{c.name}: {' → '.join(c.path_names)}")

    # Execute via cat
    result = await cat.chain_registry.run("full_reasoning", prompt="hello")

This file has zero third-party dependencies and zero meowagent imports.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Chain:
    """A named Path sequence describing a multi-step composite operation.

    Each Chain is an ordered list of Path names. Paths must be registered
    in ``cat.path_registry`` and are called in sequence during execution.

    Attributes:
        name: Unique chain name, e.g. ``"full_reasoning"``
        path_names: Path name sequence (may be empty, e.g. diagnostic chain)
        description: Human-readable description
        rollback_paths: Rollback Path names executed in reverse on failure
            (v1.0.3)
    """

    name: str
    path_names: tuple[str, ...] = ()
    description: str = ""
    rollback_paths: tuple[str, ...] = ()


# -- Builtin chain table -----------------------------------------------------

# Named constants (v0.5.29 publicly exported)
MEMORY_SEARCH_CHAIN: Chain = Chain(
    "memory_search",
    ("locate",),
    "Memory search — search hippocampus for relevant memories",
)
FULL_REASONING_CHAIN: Chain = Chain(
    "full_reasoning",
    ("deep_reason", "speak"),
    "Reasoning + output — deep reason then speak",
)
TOOL_EXEC_CHAIN: Chain = Chain(
    "tool_exec",
    ("execute_tool",),
    "Tool execution — call paws interactive tools",
)
MAINTENANCE_CHAIN: Chain = Chain(
    "maintenance",
    ("decay", "cleanup_orphans"),
    "Self-maintenance — decay memories + cleanup orphan connections",
)
DIAGNOSTIC_CHAIN: Chain = Chain(
    "diagnostic",
    ("crystallize",),
    "Diagnostic — surface crystallizer hotspots + usage stats",
)
WORKFLOW_CHAIN: Chain = Chain(
    "workflow_chain",
    ("workflow_create", "execute_tool", "workflow_checkpoint"),
    "Workflow single-step — create → execute → archive",
)
# -- v1.3.0 Growth chains --------------------------------------------------
GROWTH_CHAIN: Chain = Chain(
    "growth_chain",
    ("record_anomaly", "crystallize"),
    "Growth chain — record anomaly pattern, then crystallize skills",
)
REFLECTION_CHAIN: Chain = Chain(
    "reflection_chain",
    ("crystallize",),
    "Reflection chain — post-execution skill review",
)

BUILTIN_CHAINS: tuple[Chain, ...] = (
    MEMORY_SEARCH_CHAIN,
    FULL_REASONING_CHAIN,
    TOOL_EXEC_CHAIN,
    MAINTENANCE_CHAIN,
    DIAGNOSTIC_CHAIN,
    WORKFLOW_CHAIN,
    GROWTH_CHAIN,
    REFLECTION_CHAIN,
)


def register_builtin_chains(registry: ChainRegistry) -> None:
    """Register builtin chains into a ChainRegistry.

    Args:
        registry: ChainRegistry instance
    """
    for c in BUILTIN_CHAINS:
        registry.register(c)


# -- ChainRegistry -------------------------------------------------


@dataclass
class ChainRegistry:
    """Chain registry — manages Chain registration, lookup, and execution.

    Usage::

        registry = ChainRegistry()
        register_builtin_chains(registry)

        # Lookup
        chain = registry.get("full_reasoning")
        all_chains = registry.list_all()

        # Execute
        result = await registry.run(cat, "full_reasoning", prompt="hello")
    """

    _chains: dict[str, Chain] = field(default_factory=dict, init=False)
    _chains_list: list[Chain] = field(default_factory=list, init=False)

    def register(self, chain: Chain) -> None:
        """Register a chain. Same-named chains overwrite old values.

        Args:
            chain: Chain instance

        Raises:
            TypeError: chain is not a Chain instance
        """
        if not isinstance(chain, Chain):
            raise TypeError(f"Expected Chain instance, got {type(chain).__name__}")
        if chain.name in self._chains:
            self._chains_list.remove(self._chains[chain.name])
        self._chains[chain.name] = chain
        self._chains_list.append(chain)

    def get(self, name: str) -> Chain | None:
        """Lookup chain by name.

        Args:
            name: Chain name

        Returns:
            Chain object, None if not found
        """
        return self._chains.get(name)

    def list_all(self) -> list[Chain]:
        """Return all registered chains in registration order."""
        return list(self._chains_list)

    async def run(self, cat: Any, name: str, **initial_input: Any) -> dict[str, Any]:
        """Execute a chain: sequentially run path_names, passing previous
        step's return value as ``**kwargs`` to the next step.

        v1.0.3: On failure, executes ``rollback_paths`` in reverse order;
        rollback exceptions do not mask the original exception.

        Args:
            cat: CatBase instance (must support
                ``cat.path_registry.run(cat, name, **kw)``)
            name: Chain name
            **initial_input: Initial input, passed as kwargs to the first path

        Returns:
            Last step's return value (wrapped as dict); empty chain returns
            ``dict(initial_input)``

        Raises:
            KeyError: Chain not found, or path referenced in chain not found
        """
        chain = self.get(name)
        if chain is None:
            raise KeyError(f"Chain '{name}' not found in registry")

        current_input: dict[str, Any] = dict(initial_input)
        last_result: Any = current_input

        try:
            for path_name in chain.path_names:
                last_result = await cat.path_registry.run(
                    cat,
                    path_name,
                    **current_input,
                )
                # previous step return value becomes next step kwargs
                current_input = last_result if isinstance(last_result, dict) else {"_result": last_result}
        except Exception:
            # execute rollback paths in reverse; rollback exceptions do not mask the original
            for rollback_name in reversed(chain.rollback_paths):
                with contextlib.suppress(Exception):
                    await cat.path_registry.run(
                        cat,
                        rollback_name,
                        **current_input,
                    )
            raise

        # return the last step result (preserving dict type)
        if isinstance(last_result, dict):
            return last_result
        return {"_result": last_result}


__all__ = [
    "Chain",
    "ChainRegistry",
    "MEMORY_SEARCH_CHAIN",
    "FULL_REASONING_CHAIN",
    "TOOL_EXEC_CHAIN",
    "MAINTENANCE_CHAIN",
    "DIAGNOSTIC_CHAIN",
    "WORKFLOW_CHAIN",
    "GROWTH_CHAIN",
    "REFLECTION_CHAIN",
    "BUILTIN_CHAINS",
    "register_builtin_chains",
]
