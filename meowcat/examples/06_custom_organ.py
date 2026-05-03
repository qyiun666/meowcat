"""Example 06: Custom organ — write an organ satisfying a Protocol and mount it.

Scenario: The user wants to add a custom organ to a cat (e.g. special audio processing).
Simply satisfy the corresponding Protocol to participate in collaboration
via wiring and the signal system.

Run: ``python -m meowcat.examples.06_custom_organ``
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

import anyio

from meowcat import CatBase, EarsProtocol, biology


class SharpEars:
    """Custom ears: auto-extract keywords. Satisfies EarsProtocol."""

    name = "sharp-ears"

    async def hear(self, raw_input: str) -> dict:
        return {"text": raw_input, "source": "sharp-ears"}

    def extract_keywords(self, text: str, top_k: int = 5) -> list[str]:
        words = [w for w in text.split() if len(w) > 1]
        return words[:top_k]

    def detect_language(self, text: str) -> str:
        return "zh" if any("\u4e00" <= c <= "\u9fff" for c in text) else "en"

    def diagnose(self) -> dict:
        return {"name": self.name, "type": "custom-ears"}


async def main() -> None:
    # 1. Create cat
    cat = CatBase("custom-organ-cat")

    # 2. Mount custom organ — with Protocol validation
    cat.mount("sense", "sharp-ears", SharpEars(), protocol=EarsProtocol)

    # 3. Assemble default wiring table
    biology.apply_default_wiring(cat._nervous.wiring)

    # 4. Add custom organ to wiring (make it accessible to other organs)
    cat._nervous.wiring.connect(("sense", "sharp-ears"), ("brain", "thalamus"))
    cat._nervous.freeze()

    # 5. Directly access organ
    ears = cat.organ("sense", "sharp-ears")
    print(f"mounted: {ears.name}")
    print(f"keywords: {ears.extract_keywords('hello world from meowcat')}")
    print(f"diagnose: {ears.diagnose()}")

    print("custom organ OK")


if __name__ == "__main__":
    anyio.run(main)
