# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""Example 05: Minimal chat cat — using the Path/Chain/Loop four-layer system.

Scenario: The simplest cat, mounting only essential organs, demonstrating
Path/Chain/Loop registration and execution. Uses CatBase directly
(without create_cat) to show low-level flexibility.

Run: ``python -m meowcat.examples.05_minimal_chat_cat``
"""


from __future__ import annotations

import anyio

from meowcat import CatBase, Path, Chain, Loop, biology


class EchoBrain:
    """Minimal brain: echo input back."""

    name = "cerebrum"

    async def generate(self, prompt: str = "", **kw) -> str:
        # Chain data flow: listen returns {"text": ...} passed in as kw
        p = prompt or kw.get("text", str(kw))
        return f"Meow! You asked: {p[:60]}"


class SimpleMouth:
    """Minimal mouth: print reply."""

    name = "mouth"

    async def speak(self, text: str = "", **kw) -> str:
        # Chain data flow: previous step result may be passed as _result
        msg = text or kw.get("_result", str(kw))
        print(f"🐱: {msg}")
        return msg


class SimpleEars:
    """Minimal ears: pass through text directly."""

    name = "ears"

    async def hear(self, raw_input: str) -> dict:
        return {"text": str(raw_input)}


async def main() -> None:
    # 1. Create cat + mount minimal organs
    cat = CatBase("minimal-cat")
    echo = EchoBrain()
    cat.mount("brain", "cerebrum", echo)
    # Same instance, cerebrum→cerebellum default wiring already connected
    cat.mount("brain", "cerebellum", echo)
    cat.mount("voice",  "mouth",  SimpleMouth())
    cat.mount("sense", "ears",   SimpleEars())

    # 2. Assemble custom wiring + freeze
    biology.apply_default_wiring(cat._nervous.wiring)
    # Add custom pathway: ears → cerebrum (not in default wiring)
    cat._nervous.wiring.connect(("sense", "ears"), ("brain", "cerebrum"))
    cat._nervous.freeze()

    # 3. Register custom Paths
    cat.path_registry.register(Path(
        "hear_local", ("sense", "ears"), ("sense", "ears"),
        "hear", "read", "Ear self-loop — receive text input",
    ))
    cat.path_registry.register(Path(
        "think", ("sense", "ears"), ("brain", "cerebrum"),
        "generate", "read", "Ears→Brain — reasoning",
    ))
    cat.path_registry.register(Path(
        "speak_local", ("brain", "cerebellum"), ("voice", "mouth"),
        "speak", "write", "Cerebellum→Mouth output",
    ))

    # 4. Register Chain: hear→think→speak
    cat.chain_registry.register(Chain(
        "quick_chat", ("hear_local", "think", "speak_local"), "Quick chat",
    ))

    # 5. Register Loop
    cat.loop_registry.register(Loop(
        "quick_chat_loop", "Quick chat loop",
        chain=cat.chain_registry.get("quick_chat"),
    ))

    # 6. Execute
    print("=== Chain: quick_chat ===")
    result = await cat.chain_registry.run(cat, "quick_chat", raw_input="hello world")
    print(f"Chain result: {result}")

    print("\n=== Loop: quick_chat_loop ===")
    result = await cat.loop_registry.run(cat, "quick_chat_loop", raw_input="what is your name")
    print(f"Loop result: {result}")

    # 7. View registries
    print("\n=== Paths ===")
    for p in cat.path_registry.list_all():
        print(f"  {p.name}: {p.from_organ} → {p.to_organ}.{p.method}")
    print("\n=== Chains ===")
    for c in cat.chain_registry.list_all():
        names = " → ".join(c.path_names) if c.path_names else "(empty)"
        print(f"  {c.name}: {names}")
    print("\n=== Loops ===")
    for lp in cat.loop_registry.list_all():
        print(f"  {lp.name}: trigger={lp.trigger}, chain={lp.chain.name}")

    print("\nminimal chat cat OK")


if __name__ == "__main__":
    anyio.run(main)

