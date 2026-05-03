"""meowcat Colony — Cat container (v1.0.2) + Federation (v1.0.12).

Colony manages peer-to-peer collaboration + shared storage for multiple cats.
Cats created in a colony are automatically registered and share storage.

v1.0.12: Federation — cross-host Colony mutual awareness, communication (federate + signal_remote).

Orthogonal to Kitten (master/slave mode):
- Kitten: master cat spawns kitten → result delivered back (parent → child)
- Colony: multiple independent cats collaborate equally (peer ↔ peer), sharing state via SharedStorage
- Colony Federation: cross-host Colony peer-to-peer communication (colony ↔ colony), via FederationTransport
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from meowcat.assembly import CatBase
from meowcat.errors import IllegalNeuralPathError
from meowcat.protocols import SharedStorageProtocol
from meowcat.protocols_storage import FederationTransport

logger = logging.getLogger("meowcat.colony")


class Colony:
    """Cat container — manages peer-to-peer collaboration + shared storage.

    Typical usage::

        from meowcat import Colony, CatBase
        from meowcat.defaults import InMemorySharedStore

        colony = Colony("my-colony", storage=InMemorySharedStore())

        # Create cats (auto-register + shared storage)
        cat_a = colony.create_cat("a")
        cat_b = colony.create_cat("b", parent_id="a")

        # Inter-cat communication
        result = await colony.signal_between(
            "a", "b", "brain", "hippocampus", "locate",
            query="hello",
        )

        # Result delivery
        await colony.deliver_result("a", "b", {"done": True})

        # Broadcast
        results = await colony.broadcast("health_check")

    **Cross-cat wiring validation**:
    Colony maintains optional ``cross_wiring`` (cross-cat wiring table).
    When set, ``signal_between()`` validates whether the cross-cat edge is allowed.
    When not set, cross-cat signal skips wiring validation (pass through).
    """

    # -- Cross-cat wiring edge type ------------------------------------
    # (from_cat_id, to_cat_id) allowlist/blocklist
    _CrossEdge = tuple[str, str]

    def __init__(
        self,
        colony_id: str,
        storage: SharedStorageProtocol,
        *,
        cross_wiring_allowed: set[_CrossEdge] | None = None,
        cross_wiring_forbidden: set[_CrossEdge] | None = None,
    ) -> None:
        """Construct a cat container.

        Args:
            colony_id: Unique identifier for the colony.
            storage: Shared storage instance (satisfying SharedStorageProtocol).
            cross_wiring_allowed: Cross-cat allowlist edges. None = no validation (allow all by default).
            cross_wiring_forbidden: Cross-cat blocklist edges (higher priority than allowlist).
        """
        self.colony_id = colony_id
        self._storage = storage
        self._cats: dict[str, CatBase] = {}
        self._cross_allowed: set[Colony._CrossEdge] = cross_wiring_allowed or set(
        )
        self._cross_forbidden: set[Colony._CrossEdge] = cross_wiring_forbidden or set(
        )
        self._has_cross_wiring = (
            cross_wiring_allowed is not None or cross_wiring_forbidden is not None
        )
        # -- Federation (v1.0.12) ------------------------------------------
        self._transport: FederationTransport | None = None
        self._federation_task: asyncio.Task | None = None
        self._pending_remote: dict[str, asyncio.Future] = {}
        self._federated = False

    # -- Cross-cat wiring ---------------------------------------------

    def allow_cross(self, from_cat: str, to_cat: str) -> None:
        """Declare a cross-cat allowlist edge (from_cat → to_cat allows signal)."""
        self._cross_allowed.add((from_cat, to_cat))
        self._has_cross_wiring = True

    def forbid_cross(self, from_cat: str, to_cat: str) -> None:
        """Declare a cross-cat blocklist edge (from_cat → to_cat forbids signal)."""
        self._cross_forbidden.add((from_cat, to_cat))
        self._has_cross_wiring = True

    def _assert_cross_allowed(self, from_id: str, to_id: str) -> None:
        """Validate whether cross-cat edge is allowed.

        Raises:
            IllegalNeuralPathError: Cross-cat edge is not allowed.
        """
        if not self._has_cross_wiring:
            return  # No cross_wiring set → pass through

        if (from_id, to_id) in self._cross_forbidden:
            raise IllegalNeuralPathError(
                ("colony", from_id), ("colony", to_id),
                reason=f"cross-cat signal forbidden: {from_id} → {to_id}",
            )

        if self._cross_allowed and (from_id, to_id) not in self._cross_allowed:
            raise IllegalNeuralPathError(
                ("colony", from_id), ("colony", to_id),
                reason=f"cross-cat signal not allowed: {from_id} → {to_id}",
            )

    # -- Create -------------------------------------------------------

    def create_cat(
        self,
        cat_id: str,
        *,
        parent_id: str | None = None,
        allowed_organs: frozenset[str] | None = None,
        memory_snapshot: dict | None = None,
        **cat_kwargs: Any,
    ) -> CatBase:
        """Create a cat in the colony and auto-register it.

        Args:
            cat_id: Unique identifier for the cat.
            parent_id: Parent cat identifier (string, no object reference).
            allowed_organs: Organ access allowlist, None = allow all.
            memory_snapshot: Context slice assigned by parent cat (written to shared storage).
            **cat_kwargs: Additional arguments passed to CatBase.

        Returns:
            Registered CatBase instance.
        """
        cat = CatBase(
            cat_id,
            parent_id=parent_id,
            allowed_organs=allowed_organs,
            **cat_kwargs,
        )
        # Inject shared storage reference
        cat._colony_storage = self._storage  # type: ignore[attr-defined]

        # Inject memory_snapshot (context slice)
        if memory_snapshot:
            # type: ignore[attr-defined]
            cat._memory_snapshot = memory_snapshot

        self.register(cat)
        return cat

    # -- Register / Remove --------------------------------------------

    def register(self, cat: CatBase) -> None:
        """Register a cat into the colony (overwrites if already exists).

        Args:
            cat: CatBase instance.
        """
        cat._colony_storage = self._storage  # type: ignore[attr-defined]
        self._cats[cat.cat_id] = cat

    def unregister(self, cat_id: str) -> None:
        """Remove a cat from the colony.

        Args:
            cat_id: Unique identifier for the cat.

        Raises:
            KeyError: Cat does not exist.
        """
        del self._cats[cat_id]

    def get_cat(self, cat_id: str) -> CatBase:
        """Get a cat by ID.

        Args:
            cat_id: Unique identifier for the cat.

        Returns:
            CatBase instance.

        Raises:
            KeyError: Cat does not exist.
        """
        return self._cats[cat_id]

    def list_cats(self) -> list[str]:
        """List all cat IDs in the colony.

        Returns:
            List of cat_id strings.
        """
        return list(self._cats.keys())

    # -- Alias methods (v1.0.9) ---------------------------------------

    def adopt(self, cat: CatBase) -> None:
        """Adopt a cat (semantic alias for register).

        Args:
            cat: CatBase instance.
        """
        self.register(cat)

    def release(self, cat_id: str) -> None:
        """Release a cat (semantic alias for unregister).

        Args:
            cat_id: Unique identifier for the cat.

        Raises:
            KeyError: Cat does not exist.
        """
        self.unregister(cat_id)

    # -- Shared storage (namespace isolation) -------------------------

    def _ns_key(self, cat_id: str, key: str) -> str:
        """Construct a namespace-isolated storage key.

        cat_id prefix provides automatic isolation: ``cat-a/memories/xxx`` vs ``cat-b/memories/xxx``.
        """
        return f"{cat_id}/{key}"

    async def storage_get(self, cat_id: str, key: str) -> Any:
        """Cat reads from shared storage (auto cat_id prefix isolation)."""
        return await self._storage.get(self._ns_key(cat_id, key))

    async def storage_set(self, cat_id: str, key: str, value: Any) -> None:
        """Cat writes to shared storage (auto cat_id prefix isolation)."""
        await self._storage.set(self._ns_key(cat_id, key), value)

    async def storage_delete(self, cat_id: str, key: str) -> None:
        """Cat deletes a shared storage entry."""
        await self._storage.delete(self._ns_key(cat_id, key))

    async def storage_list_keys(self, cat_id: str) -> list[str]:
        """List all shared storage keys for a cat (prefix stripped)."""
        prefix = f"{cat_id}/"
        all_keys = await self._storage.list_keys()
        return [
            k[len(prefix):] for k in all_keys if k.startswith(prefix)
        ]

    async def storage_watch(
        self, cat_id: str, pattern: str,
    ) -> Any:
        """Watch shared storage key changes matching pattern.

        Delegates to the underlying storage.watch(). Returns AsyncIterator.
        """
        ns_pattern = f"{cat_id}/{pattern}"
        # type: ignore[attr-defined]
        async for item in self._storage.watch(ns_pattern):
            yield item

    # -- Result delivery ---------------------------------------------

    async def deliver_result(
        self, parent_id: str, from_kitten: str, result: Any,
    ) -> None:
        """Kitten delivers result back to parent cat.

        Writes to shared storage ``{parent_id}/kitten:{from_kitten}/result``.

        Args:
            parent_id: Parent cat ID.
            from_kitten: Kitten ID.
            result: Arbitrary result to deliver.
        """
        key = f"kitten:{from_kitten}/result"
        await self.storage_set(parent_id, key, result)

    # -- Broadcast ----------------------------------------------------

    async def broadcast(self, event: str, **data: Any) -> list[Any]:
        """Broadcast an event to all cats in the colony.

        Emits the same event to every cat, collecting all handler return values.

        Args:
            event: Event name.
            **data: Event data.

        Returns:
            List of return values from all cat handlers.
        """
        results: list[Any] = []
        for cat in self._cats.values():
            await cat.emit(event, data)
        return results

    async def health_check_all(self) -> dict[str, dict]:
        """Run health check on all cats.

        Returns:
            ``{cat_id: {...diagnose...}, ...}``
        """
        results: dict[str, dict] = {}
        for cat_id, cat in self._cats.items():
            try:
                results[cat_id] = await cat.health_check()
            except Exception as exc:
                results[cat_id] = {"error": str(exc)}
        return results

    # -- Inter-cat communication --------------------------------------

    async def signal_between(
        self,
        from_id: str,
        to_id: str,
        to_category: str,
        to_name: str,
        method: str,
        *args: Any,
        **kw: Any,
    ) -> Any:
        """Inter-cat signal communication.

        One cat sends a signal to another cat's organ via the colony.

        Flow:
        1. Validate cross-cat wiring (if cross_wiring is set)
        2. Retrieve target organ from target cat
        3. Directly invoke method on target organ

        Args:
            from_id: Sender cat ID.
            to_id: Receiver cat ID.
            to_category: Target organ category (e.g. "brain").
            to_name: Target organ name (e.g. "hippocampus").
            method: Target method name.
            *args, **kw: Forwarded to target method.

        Returns:
            Return value of target method.

        Raises:
            KeyError: Sender or receiver cat does not exist.
            IllegalNeuralPathError: Cross-cat edge is not allowed.
            OrganNotMountedError: Target organ does not exist.
        """
        # 1. Cross-cat wiring validation
        self._assert_cross_allowed(from_id, to_id)

        # 2. Get target cat
        target_cat = self._cats[to_id]

        # 3. Retrieve target organ
        target_organ = target_cat.organ(to_category, to_name)

        # 4. Invoke method
        fn = getattr(target_organ, method)
        import inspect as _inspect
        result = fn(*args, **kw)
        if _inspect.isawaitable(result):
            result = await result
        return result

    # -- Convenience methods ------------------------------------------

    @property
    def cat_count(self) -> int:
        """Number of cats in the colony."""
        return len(self._cats)

    # -- Federation (v1.0.12) -----------------------------------------

    @property
    def is_federated(self) -> bool:
        """Whether federation is enabled."""
        return self._federated

    async def federate(self, transport: FederationTransport) -> None:
        """Enable federation, join the cross-host Colony network.

        Starts the transport layer and begins listening for inbound messages
        from other Colonies. After pairing with federate(), you can call
        signal_remote() to send signals to cats in remote Colonies.

        Args:
            transport: Federation transport instance (e.g. TCPSocketTransport or RedisPubSubTransport).

        Raises:
            RuntimeError: Already federated.
        """
        if self._federated:
            raise RuntimeError(
                f"Colony '{self.colony_id}' is already federated")

        self._transport = transport
        await transport.start()
        self._federated = True
        self._federation_task = asyncio.create_task(
            self._federation_loop(),
            name=f"colony-federation-{self.colony_id}",
        )
        logger.info("Colony '%s' federated", self.colony_id)

    async def unfederate(self) -> None:
        """Disable federation, disconnect cross-host connections."""
        if not self._federated:
            return

        if self._federation_task:
            self._federation_task.cancel()
            try:
                await self._federation_task
            except asyncio.CancelledError:
                pass
            self._federation_task = None

        if self._transport:
            await self._transport.stop()
            self._transport = None

        # Cancel all pending remote requests
        for fut in self._pending_remote.values():
            if not fut.done():
                fut.cancel()
        self._pending_remote.clear()

        self._federated = False
        logger.info("Colony '%s' unfederated", self.colony_id)

    async def signal_remote(
        self,
        target_colony: str,
        cat_id: str,
        to_category: str,
        to_name: str,
        method: str,
        *args: Any,
        **kw: Any,
    ) -> Any:
        """Send a signal to a cat in a remote Colony and wait for response.

        Requires this Colony to have called federate() to enable federation.
        The remote Colony wiring still applies — the remote cat's own wiring
        validates whether the target organ and method are accessible.

        Args:
            target_colony: Remote colony_id.
            cat_id: Remote cat ID.
            to_category: Target organ category.
            to_name: Target organ name.
            method: Target method name.
            *args, **kw: Forwarded to target method.

        Returns:
            Return value of the remote method (must be JSON-serializable).

        Raises:
            RuntimeError: This Colony is not federated.
            ConnectionError: Cannot reach the remote.
            TimeoutError: Timed out waiting for remote response.
            IllegalNeuralPathError: Remote wiring rejected the pathway.
        """
        if not self._federated or self._transport is None:
            raise RuntimeError(
                f"Colony '{self.colony_id}' is not federated. "
                f"Call colony.federate(transport) first."
            )

        request_id = uuid.uuid4().hex
        payload: dict[str, Any] = {
            "type": "signal_request",
            "request_id": request_id,
            "from_colony": self.colony_id,
            "to_cat": cat_id,
            "to_category": to_category,
            "to_name": to_name,
            "method": method,
            "args": args,
            "kw": kw,
        }

        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_remote[request_id] = fut

        try:
            await self._transport.publish(target_colony, payload)
            result = await asyncio.wait_for(fut, timeout=30.0)
            if result.get("error"):
                raise IllegalNeuralPathError(
                    ("colony", cat_id), (to_category, to_name),
                    reason=result["error"],
                )
            return result.get("data")
        finally:
            self._pending_remote.pop(request_id, None)

    async def _federation_loop(self) -> None:
        """Federation background loop: receive inbound messages and dispatch."""
        if self._transport is None:
            return

        try:
            async for msg in self._transport.subscribe(self.colony_id):
                await self._handle_federation_message(msg)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception(
                "Federation loop error in colony '%s'", self.colony_id)

    async def _handle_federation_message(self, msg: dict) -> None:
        """Handle an inbound federation message."""
        msg_type = msg.get("type")

        if msg_type == "signal_request":
            await self._handle_signal_request(msg)
        elif msg_type == "signal_response":
            self._handle_signal_response(msg)
        else:
            logger.warning("Unknown federation message type: %s", msg_type)

    async def _handle_signal_request(self, msg: dict) -> None:
        """Handle a signal request from a remote."""
        request_id = msg["request_id"]
        from_colony = msg.get("from_colony", "unknown")
        cat_id = msg["to_cat"]
        to_category = msg["to_category"]
        to_name = msg["to_name"]
        method = msg["method"]
        args = msg.get("args", ())
        kw = msg.get("kw", {})

        response: dict[str, Any] = {
            "type": "signal_response",
            "request_id": request_id,
            "from_colony": self.colony_id,
        }

        # Verify target cat exists
        if cat_id not in self._cats:
            response["error"] = f"Cat '{cat_id}' not found in colony '{self.colony_id}'"
        else:
            try:
                # Get target cat and organ
                target_cat = self._cats[cat_id]
                target_organ = target_cat.organ(to_category, to_name)
                fn = getattr(target_organ, method)

                import inspect as _inspect
                result = fn(*args, **kw)
                if _inspect.isawaitable(result):
                    result = await result

                response["data"] = result
            except Exception as exc:
                response["error"] = str(exc)

        # Send response back
        if self._transport:
            try:
                await self._transport.publish(from_colony, response)
            except Exception:
                logger.exception(
                    "Failed to send signal_response to '%s'", from_colony,
                )

    def _handle_signal_response(self, msg: dict) -> None:
        """Handle a signal response from a remote."""
        request_id = msg["request_id"]
        fut = self._pending_remote.get(request_id)
        if fut and not fut.done():
            fut.set_result(msg)


__all__ = ["Colony", "FederationTransport"]
