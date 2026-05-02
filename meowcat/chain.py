"""meowcat 链路 — Chain dataclass + ChainRegistry + 内置链路表。

链路是一组有名字的 Path 序列，可以是不要求闭环的多步操作组合。
ChainRegistry 管理所有已注册链路，提供按名查询和顺序执行能力。

对外部开发者的体验::

    from meowcat.chain import Chain, BUILTIN_CHAINS

    # 查看内置链路
    for c in BUILTIN_CHAINS:
        print(f"{c.name}: {' → '.join(c.path_names)}")

    # 通过 cat 执行
    result = await cat.chain_registry.run("full_reasoning", prompt="你好")

本文件零第三方依赖，零 meowagent import。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Chain:
    """一组命名的 Path 序列，描述多步协作的复合操作。

    每条 Chain 是一组 Path 名称的有序列表。Path 必须已注册在
    ``cat.path_registry`` 中，执行时按序调用。

    Attributes:
        name: 链路唯一名称，如 ``"full_reasoning"``
        path_names: Path 名称序列（可为空，如 diagnostic 链路）
        description: 人类可读描述
        rollback_paths: 失败时逆序执行的回滚 Path 名称序列（v1.0.3）
    """

    name: str
    path_names: tuple[str, ...] = ()
    description: str = ""
    rollback_paths: tuple[str, ...] = ()


# -- 内置链路表 ----------------------------------------------------

# 具名常量（v0.5.29 公开导出）
MEMORY_SEARCH_CHAIN: Chain = Chain(
    "memory_search", ("locate",),
    "记忆检索 — 从海马体搜索相关记忆",
)
FULL_REASONING_CHAIN: Chain = Chain(
    "full_reasoning", ("deep_reason", "speak"),
    "推理+输出 — 深度推理后发言",
)
TOOL_EXEC_CHAIN: Chain = Chain(
    "tool_exec", ("execute_tool",),
    "工具执行 — 调用爪子交互工具",
)
MAINTENANCE_CHAIN: Chain = Chain(
    "maintenance", ("decay", "cleanup_orphans"),
    "自维护 — 衰减记忆 + 清理孤立连接",
)
DIAGNOSTIC_CHAIN: Chain = Chain(
    "diagnostic", (),
    "诊断 — 空链路，走 Stethoscope 体检",
)

BUILTIN_CHAINS: tuple[Chain, ...] = (
    MEMORY_SEARCH_CHAIN,
    FULL_REASONING_CHAIN,
    TOOL_EXEC_CHAIN,
    MAINTENANCE_CHAIN,
    DIAGNOSTIC_CHAIN,
)


def register_builtin_chains(registry: "ChainRegistry") -> None:
    """将内置链路注册到 ChainRegistry。

    Args:
        registry: 链路注册中心实例
    """
    for c in BUILTIN_CHAINS:
        registry.register(c)


# -- ChainRegistry -------------------------------------------------

@dataclass
class ChainRegistry:
    """链路注册中心 — 管理 Chain 的注册、查询和执行。

    用法::

        registry = ChainRegistry()
        register_builtin_chains(registry)

        # 查询
        chain = registry.get("full_reasoning")
        all_chains = registry.list_all()

        # 执行
        result = await registry.run(cat, "full_reasoning", prompt="你好")
    """

    _chains: dict[str, Chain] = field(default_factory=dict, init=False)
    _chains_list: list[Chain] = field(default_factory=list, init=False)

    def register(self, chain: Chain) -> None:
        """注册一条链路。同名链路覆盖旧值。

        Args:
            chain: Chain 实例

        Raises:
            TypeError: chain 不是 Chain 实例
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
        """按名查找链路。

        Args:
            name: 链路名称

        Returns:
            Chain 对象，不存在返回 None
        """
        return self._chains.get(name)

    def list_all(self) -> list[Chain]:
        """返回所有已注册链路列表（注册顺序）。"""
        return list(self._chains_list)

    async def run(self, cat: Any, name: str, **initial_input: Any) -> dict[str, Any]:
        """执行一条链路：按序跑 path_names，前一步返回值作为下一步的 **kwargs。

        v1.0.3: 失败时逆序执行 ``rollback_paths``，回滚异常不掩盖原始异常。

        Args:
            cat: CatBase 实例（需支持 ``cat.path_registry.run(cat, name, **kw)``）
            name: 链路名称
            **initial_input: 初始输入，作为第一条 path 的 kwargs

        Returns:
            最后一步的返回值（包装为 dict），空链路返回 ``dict(initial_input)``

        Raises:
            KeyError: 链路不存在，或链路中引用的 path 不存在
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
    "BUILTIN_CHAINS", "register_builtin_chains",
]
