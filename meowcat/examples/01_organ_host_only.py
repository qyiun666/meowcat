"""Example 01: OrganHost only — use as an organ container with Protocol validation.

Scenario: The user just wants a dict that "mounts/gets objects by (category, name)",
and wants automatic ``isinstance(obj, Protocol)`` validation on mount.
No need for nervous system / reflex / events.

Run: ``python -m meowcat.examples.01_organ_host_only``
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

from meowcat import OrganHost
from meowcat.protocols import OrganProtocol


class Cerebrum:
    name = "cerebrum"

    async def generate(self, prompt: str) -> str:
        return "meow"


def main() -> None:
    host = OrganHost(uid="demo")

    # Mount — with Protocol validation (isinstance must pass)
    host.mount("brain", "cerebrum", Cerebrum(), protocol=OrganProtocol)
    host.mount("sense", "ears", type("Ears", (), {"name": "ears"})())

    # Retrieve
    brain = host.organ("brain", "cerebrum")
    print(f"got {brain.name}")

    # Query
    assert host.has_organ("sense", "ears")
    print(f"brain organs: {list(host.organs('brain').keys())}")

    # Validate required mount list
    host.assert_organs_mounted([("brain", "cerebrum"), ("sense", "ears")])

    # Unmount
    host.unmount("sense", "ears")
    assert not host.has_organ("sense", "ears")
    print("OrganHost standalone OK")


if __name__ == "__main__":
    main()
