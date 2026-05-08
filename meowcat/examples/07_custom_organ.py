# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""Example 07: Custom organ + Path + Chain + Loop full example.

Scenario: Add a "nose" organ to the cat, declare Paths, assemble Chains,
register Loops — demonstrating the four-layer extension flow from
Organ → Path → Chain → Loop.

Run: ``python -m meowcat.examples.07_custom_organ``
"""

from __future__ import annotations

import anyio

from meowcat import CatBase, Chain, Loop, Path, biology


class MyNose:
    """Custom nose: implements olfactory input."""

    name = "nose"

    def diagnose(self) -> dict:
        return {"name": self.name, "type": "custom-nose"}

    async def sniff(self, input_data: str) -> dict:
        """Analyze scent information in the input."""
        smells = ["fish", "catnip", "milk", "rain", "nothing"]
        found = [s for s in smells if s in input_data.lower()]
        return {"smell": found[0] if found else "nothing", "source": "nose"}


class EchoMouth:
    """Simplified mouth: prints output."""

    name = "mouth"

    def diagnose(self) -> dict:
        return {"name": self.name}

    async def say(self, text: str = "", **kw) -> dict:
        # Chain data flow: previous step result may be passed as **kw
        if not text and kw:
            text = str(kw)
        print(f"🐱 Cat says: {text}")
        return {"spoken": text}


async def main() -> None:
    # 1. Create cat
    cat = CatBase("custom-organ-cat")

    # 2. Mount custom organs
    cat.mount(
        "sense",
        "ears",
        type("NoopEars", (), {"name": "ears", "diagnose": lambda: {}})(),
        protocol=None,
    )
    cat.mount("sense", "nose", MyNose())
    cat.mount("voice", "echo_mouth", EchoMouth())

    # 3. Assemble default wiring + add custom pathways
    biology.apply_default_wiring(cat._nervous.wiring)
    cat._nervous.wiring.connect(("sense", "ears"), ("sense", "nose"))
    cat._nervous.wiring.connect(("sense", "nose"), ("voice", "echo_mouth"))
    cat._nervous.freeze()

    # 4. Register custom Paths
    sniff_path = Path(
        "sniff",
        ("sense", "ears"),
        ("sense", "nose"),
        "sniff",
        "read",
        "Olfactory input — nose analyzes scent",
    )
    cat.path_registry.register(sniff_path)

    speak_path = Path(
        "say_local",
        ("sense", "nose"),
        ("voice", "echo_mouth"),
        "say",
        "write",
        "Output — mouth speaks",
    )
    cat.path_registry.register(speak_path)

    # 5. Register custom Chain
    smell_chain = Chain(
        "smell_then_speak",
        ("sniff", "say_local"),
        "Smell it then say it",
    )
    cat.chain_registry.register(smell_chain)

    # 6. Register custom Loop
    sniff_loop = Loop(
        "nose_patrol",
        "Nose patrol loop — sniff→say",
        chain=smell_chain,
        trigger=None,  # manual trigger
    )
    cat.loop_registry.register(sniff_loop)

    # 7. Demonstrate
    print("=== Path level: run sniff directly ===")
    result = await cat.path_registry.run(cat, "sniff", input_data="I smell fish")
    print(f"Path result: {result}")

    print("\n=== Chain level: smell_then_speak ===")
    result = await cat.chain_registry.run(cat, "smell_then_speak", input_data="I smell catnip")
    print(f"Chain result: {result}")

    print("\n=== Loop level: nose_patrol ===")
    result = await cat.loop_registry.run(cat, "nose_patrol", input_data="I smell rain")
    print(f"Loop result: {result}")

    # 8. Query registries
    print("\n=== Registered Paths ===")
    for p in cat.path_registry.list_all():
        print(f"  {p.name}: {p.from_organ} → {p.to_organ}.{p.method}")

    print("\n=== Registered Chains ===")
    for c in cat.chain_registry.list_all():
        print(f"  {c.name}: {' → '.join(c.path_names)}")

    print("\n=== Registered Loops ===")
    for lp in cat.loop_registry.list_all():
        print(f"  {lp.name}: trigger={lp.trigger}, chain={lp.chain.name}")

    print("\ncustom organ OK")


if __name__ == "__main__":
    anyio.run(main)
