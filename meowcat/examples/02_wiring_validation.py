# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""Example 02: Wiring only — pure data structure, offline pathway validation.

Scenario: The user defines a set of neural signal paths in business code
and wants to offline-validate them first (source and target on same wiring
graph, no duplicates, bidirectional edges auto-symmetrized), then go live.

Run: ``python -m meowcat.examples.02_wiring_validation``
"""


from __future__ import annotations

from meowcat import Wiring, biology


def main() -> None:
    wiring = Wiring()
    biology.apply_default_wiring(wiring)

    print(f"Default wiring edge count: {len(wiring.edges())}")

    # Valid path (default ears → thalamus)
    wiring.assert_allowed(("sense", "ears"), ("brain", "thalamus"))
    print("(sense,ears) → (brain,thalamus) ✓")

    # Invalid path (default wiring: cerebrum not directly connected to paws)
    try:
        wiring.assert_allowed(("brain", "cerebrum"), ("sense", "paws"))
    except Exception as e:
        print(f"(brain,cerebrum) → (sense,paws) blocked: {type(e).__name__}")

    # After freeze, cannot modify
    wiring.freeze()
    try:
        wiring.add_edge(("brain", "cerebrum"), ("sense", "paws"))
    except Exception as e:
        print(f"add_edge after freeze blocked: {type(e).__name__}")

    print("Wiring standalone OK")


if __name__ == "__main__":
    main()

