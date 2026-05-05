"""Federation mixin — cross-host Colony peer-to-peer communication.

Provides federate / unfederate / signal_remote for Colony instances.
Imported into :class:`~meowcat.colony.Colony` as a mixin base class.
"""
# (c) 2025-2026 Axonant. MIT License.

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, TYPE_CHECKING

from meowcat.errors import IllegalNeuralPathError

if TYPE_CHECKING:
    from meowcat.protocols_storage import FederationTransport

logger = logging.getLogger("meowcat.colony")


class _FederationMixin:
    """Federation methods mixed into :class:`~meowcat.colony.Colony`.

    Requires the host class to define:
        - ``self._transport: FederationTransport | None``
        - ``self._federation_task: asyncio.Task | None``
        - ``self._pending_remote: dict[str, asyncio.Future]``
        - ``self._federated: bool``
        - ``self.colony_id: str``
        - ``self._cats: dict[str, CatBase]``
    """

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
        cat_uid: str,
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
            cat_uid: Remote cat ID.
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
            "to_cat": cat_uid,
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
                    ("colony", cat_uid), (to_category, to_name),
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
        cat_uid = msg["to_cat"]
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
        if cat_uid not in self._cats:
            response["error"] = f"Cat '{cat_uid}' not found in colony '{self.colony_id}'"
        else:
            try:
                # Get target cat and organ
                target_cat = self._cats[cat_uid]
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
