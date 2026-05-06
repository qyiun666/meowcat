# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat storage protocols — persistence storage interfaces.

All typing.Protocol (duck typing), zero third-party dependencies.
"""


from __future__ import annotations

from typing import Any, AsyncIterator, Protocol, runtime_checkable
import warnings

__all__ = [
    "GraphStorageProtocol", "L6StorageProtocol",
    "VectorStorageProtocol", "SharedStorageProtocol",
    "FederationTransport",
]


@runtime_checkable
class GraphStorageProtocol(Protocol):
    """Entanglement graph persistence storage interface.

    **Position**: none (storage layer, no organ coordinate)
    **Inbound**: held directly by Hippocampus, not called via wiring
    **Outbound**: none
    **Reflex Arc**: none
    **Implemented by**: app layer (storage backend)
    """

    async def load(self, cat_uid: str) -> dict[str, Any]: ...
    async def save(self, cat_uid: str, graph_data: dict[str, Any]) -> None: ...


@runtime_checkable
class L6StorageProtocol(Protocol):
    """L6 raw dialogue persistence storage interface.

    **Position**: none (storage layer, no organ coordinate)
    **Inbound**: held directly by BrainStem, not called via wiring
    **Outbound**: none
    **Reflex Arc**: none
    **Implemented by**: app layer (storage backend)
    """

    def append(self, cat_uid: str, turn: int,
               user_msg: str, ai_reply: str) -> None: ...
# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT


    def load_all(self, cat_uid: str) -> list[dict[str, Any]]: ...
    def load_recent(self, cat_uid: str,
                    n: int = 20) -> list[dict[str, Any]]: ...

    def total_chars(self, cat_uid: str) -> int: ...
    def get_stats(self, cat_uid: str) -> dict[str, Any]: ...


@runtime_checkable
class VectorStorageProtocol(Protocol):
    """Vector search storage interface (semantic search).

    **Position**: none (storage layer, no organ coordinate)
    **Inbound**: optionally held by Thalamus, not called via wiring
    **Outbound**: none
    **Reflex Arc**: none
    **Implemented by**: app layer (storage backend)
    """

    def add(self, text: str, metadata: dict[str, Any]) -> str: ...
    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]: ...
    def delete(self, doc_id: str) -> bool: ...


@runtime_checkable
class SharedStorageProtocol(Protocol):
    """Deprecated: use :class:`meowcat.storage.SharedStore` instead.

    This protocol only covers sync load/save/merge. Colony now requires
    async get/set/delete/list_keys/watch from SharedStore.
    """

    def load(self) -> dict[str, Any]: ...
    def save(self, data: dict[str, Any]) -> None: ...
    def merge(self, delta: dict[str, Any]) -> dict[str, Any]: ...

    def __init_subclass__(cls, **kwargs: Any) -> None:
        warnings.warn(
            "SharedStorageProtocol is deprecated. "
            "Extend meowcat.storage.SharedStore instead.",
            DeprecationWarning, stacklevel=2,
        )
        super().__init_subclass__(**kwargs)


@runtime_checkable
class FederationTransport(Protocol):
    """Cross-Colony communication transport — enables Colonies on different hosts/processes to discover and communicate with each other.

    **Position**: none (transport layer, no organ coordinate)
    **Inbound**: injected by Colony.federate(), not called via wiring
    **Outbound**: none
    **Reflex Arc**: none
    **Implemented by**: framework provides TCPSocketTransport / RedisPubSubTransport; app layer may customize
    """

    async def publish(self, topic: str, payload: dict) -> None:
        """Publish a message to the specified topic.

        Args:
            topic: target colony_id.
            payload: message payload (includes type/request_id/from_cat/to_cat, etc.).
        """
        ...

    async def subscribe(self, topic: str) -> AsyncIterator[dict]:
        """Subscribe to message stream for the specified topic.

        Args:
            topic: this colony_id, receives messages sent to this colony.

        Yields:
            payload dict for each message.
        """
        ...

    async def start(self) -> None:
        """Start the transport layer (e.g. begin listening on port)."""
        ...

    async def stop(self) -> None:
        """Stop the transport layer (e.g. close port)."""
        ...

