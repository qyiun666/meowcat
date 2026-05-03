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
    "memory_search", ("locate",),
    "Memory search — search hippocampus for relevant memories",
)
FULL_REASONING_CHAIN: Chain = Chain(
    "full_reasoning", ("deep_reason", "speak"),
    "Reasoning + output — deep reason then speak",
)
TOOL_EXEC_CHAIN: Chain = Chain(
    "tool_exec", ("execute_tool",),
    "Tool execution — call paws interactive tools",
)
MAINTENANCE_CHAIN: Chain = Chain(
    "maintenance", ("decay", "cleanup_orphans"),
    "Self-maintenance — decay memories + cleanup orphan connections",
)
DIAGNOSTIC_CHAIN: Chain = Chain(
    "diagnostic", (),
    "Diagnostic — empty chain, routes through Stethoscope checkup",
)
WORKFLOW_CHAIN: Chain = Chain(
    "workflow_chain", ("workflow_create", "execute_tool",
                       "workflow_checkpoint"),
    "Workflow single-step — create → execute → archive",
)

BUILTIN_CHAINS: tuple[Chain, ...] = (
    MEMORY_SEARCH_CHAIN,
    FULL_REASONING_CHAIN,
    TOOL_EXEC_CHAIN,
    MAINTENANCE_CHAIN,
    DIAGNOSTIC_CHAIN,
    WORKFLOW_CHAIN,
)


def register_builtin_chains(registry: "ChainRegistry") -> None:
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
            raise TypeError(
                f"Expected Chain instance, got {type(chain).__name__}"
            )
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
                    cat, path_name, **current_input,
                )
                # 上一步返回值作为下一步的 kwargs
                if isinstance(last_result, dict):
                    current_input = last_result
                else:
                    current_input = {"_result": last_result}
        except Exception:
            # 逆序执行回滚路径，回滚异常不掩盖原始异常
            for rollback_name in reversed(chain.rollback_paths):
                try:
                    await cat.path_registry.run(
                        cat, rollback_name, **current_input,
                    )
                except Exception:
                    pass
            raise

        # 返回最后一步的结果（保持 dict 类型）
        if isinstance(last_result, dict):
            return last_result
        return {"_result": last_result}


__all__ = [
    "Chain", "ChainRegistry",
    "MEMORY_SEARCH_CHAIN", "FULL_REASONING_CHAIN",
    "TOOL_EXEC_CHAIN", "MAINTENANCE_CHAIN", "DIAGNOSTIC_CHAIN",
    "WORKFLOW_CHAIN",
    "BUILTIN_CHAINS", "register_builtin_chains",
]
