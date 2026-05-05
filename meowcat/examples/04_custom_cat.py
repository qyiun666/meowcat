"""Example 04: Assemble a "pocket cat" from the five subsystems.

Scenario: Without relying on ``create_cat`` / ``CatBase`` subclassing,
manually compose ``OrganHost + EventBus + Nervous + ReflexArc``
to build a minimal cat. Demonstrates the standalone assembly capability
of these subsystems.

Run: ``python -m meowcat.examples.04_custom_cat``
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

import anyio

from meowcat import (
    EventBus,
    Nervous,
    OrganHost,
    Reflex,
    ReflexArc,
    biology,
)


class Ears:
    name = "ears"

    async def hear(self, msg: str) -> str:
        return f"heard:{msg}"


class Thalamus:
    name = "thalamus"

    async def route(self, signal: str) -> str:
        return f"routed:{signal}"


async def main() -> None:
    # 1. Compose five subsystems
    host = OrganHost(uid="mini")
    events = EventBus()
    nervous = Nervous(host, events)
    reflex = ReflexArc(events, nervous)

    # 2. Mount organs
    host.mount("sense", "ears", Ears())
    host.mount("brain", "thalamus", Thalamus())

    # 3. Open pathways
    biology.apply_default_wiring(nervous.wiring)

    # 4. Register a reflex: ears → thalamus
    reflex.register(Reflex(
        name="ear_to_brain",
        trigger=lambda x: isinstance(x, str),
        path=(("sense", "ears"), ("brain", "thalamus")),
    ))

    # 5. Freeze + validate
    reflex.validate_paths()
    nervous.freeze()

    # 6. Cross-organ signal
    result = await nervous.signal(
        ("sense", "ears"), ("brain", "thalamus"),
        "route", "hello-world",
    )
    print(f"signal result: {result}")

    # 7. Match a reflex with reflex.match
    matched = reflex.match("some input")
    print(f"matched reflex: {matched.name if matched else None}")

    print("custom cat five-subsystem composition OK")


if __name__ == "__main__":
    anyio.run(main)
