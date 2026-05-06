# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""Example 03: EventBus only — pure async pub/sub, zero cat dependency.

Scenario: The user just wants an async bus for "subscribe event name → trigger callback",
not concerned with organs / pathways / reflexes.

Run: ``python -m meowcat.examples.03_event_bus_only``
"""


from __future__ import annotations

import anyio

from meowcat import EventBus


async def main() -> None:
    bus = EventBus()
    received: list[dict] = []

    async def on_user(payload: dict) -> None:
        received.append(payload)

    bus.on("user.login", on_user)
    await bus.emit("user.login", {"uid": 42, "from": "cli"})
    await bus.emit("user.login", {"uid": 7, "from": "web"})

    print(f"received {len(received)} events")
    for ev in received:
        print(f"  - {ev}")

    # Unsubscribe
    bus.off("user.login", on_user)
    await bus.emit("user.login", {"uid": 100})
    assert len(received) == 2
    print("EventBus standalone OK")


if __name__ == "__main__":
    anyio.run(main)

