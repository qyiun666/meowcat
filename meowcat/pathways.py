"""meowcat preset pathways — framework-level standard organ collaboration sequences (deprecated v0.5.27, kept for backward compatibility).

Since v0.5.27, all static methods internally delegate to ``cat.path_registry.run()``.
New code should directly use::

    from meowcat.path import Path
    result = await cat.path_registry.run("locate", query="hello")

This module preserves original API signatures for backward compatibility.

.. deprecated:: v0.5.27
    Use :class:`meowcat.path.PathRegistry` instead.
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

import warnings
from typing import Any, Callable

# ⚠️ the following imports are only for build_conversation_pipeline type reference
# all single-step pathways have migrated to meowcat.path.BUILTIN_PATHS


_warned: bool = False


def _deprecated() -> None:
    global _warned
    if not _warned:
        warnings.warn(
            "Pathways is deprecated since v0.5.27. "
            "Use cat.path_registry.run() instead.",
            DeprecationWarning, stacklevel=3,
        )
        _warned = True


class Pathways:
    """[deprecated] Preset pathway namespace.

    Since v0.5.27 all methods delegate to ``cat.path_registry.run()``.
    New code should directly use :class:`meowcat.path.PathRegistry`.
    """

    # ── Memory circuit ──

    @staticmethod
    async def remember(cat, entity_data: dict[str, Any]) -> Any:
        """[deprecated] Remember: store an entity into hippocampus.

        Delegates to ``cat.path_registry.run("remember", entity_data=entity_data)``.
        Since v0.5.26, from_organ corrected from THALAMUS to BRAINSTEM (write permission constraint).

        Args:
            cat: ``CatBase`` instance
            entity_data: Entity data dictionary
        """
        _deprecated()
        return await cat.path_registry.run(
            cat, "remember", entity_data=entity_data,
        )

    @staticmethod
    async def locate(cat, query: str) -> Any:
        """[deprecated] Locate: query memories from hippocampus.

        Delegates to ``cat.path_registry.run("locate", query=query)``.

        Args:
            cat: ``CatBase`` instance
            query: Search query
        """
        _deprecated()
        return await cat.path_registry.run(cat, "locate", query=query)

    # ── Reasoning circuit ──

    @staticmethod
    async def deep_reason(cat, prompt: str, context: str = "") -> str:
        """[deprecated] Deep reasoning: cerebrum generation.

        Delegates to ``cat.path_registry.run("deep_reason", prompt=prompt, context=context)``.

        Args:
            cat: ``CatBase`` instance
            prompt: Reasoning prompt
            context: Context (e.g. retrieved memories)

        Returns:
            Generated reasoning text
        """
        _deprecated()
        return await cat.path_registry.run(
            cat, "deep_reason", prompt=prompt, context=context,
        )

    @staticmethod
    async def fast_respond(cat, pattern: str) -> str:
        """[deprecated] Fast response: cerebellum pattern matching.

        Delegates to ``cat.path_registry.run("fast_match", pattern=pattern)``.
        Since v0.5.27, from_organ corrected from THALAMUS to BRAINSTEM (wiring constraint).

        Args:
            cat: ``CatBase`` instance
            pattern: Match pattern

        Returns:
            Matched response text
        """
        _deprecated()
        return await cat.path_registry.run(cat, "fast_match", pattern=pattern)

    # ── Output circuit ──

    @staticmethod
    async def say(cat, text: str) -> Any:
        """[deprecated] Speak: vocalize after cerebellum coordination.

        Delegates to ``cat.path_registry.run("say", text=text)``.

        Args:
            cat: ``CatBase`` instance
            text: Text to speak
        """
        _deprecated()
        return await cat.path_registry.run(cat, "say", text=text)

    # ── Full conversation pipeline (closure) ──

    @staticmethod
    def build_conversation_pipeline(
        cat,
    ) -> Callable[[str], Any]:
        """Return a closure: input text → locate memory → reason → output.

        This is the most commonly used composite pathway. Every step goes
        through wiring validation.

        Args:
            cat: ``CatBase`` instance

        Returns:
            ``async def pipeline(user_input: str) -> str`` closure
        """
        _deprecated()

        async def pipeline(user_input: str) -> str:
            # 1. Locate memory
            memory = await Pathways.locate(cat, user_input)
            context = str(memory) if memory else ""

            # 2. Reason
            reply = await Pathways.deep_reason(cat, user_input, context=context)

            # 3. Output
            await Pathways.say(cat, reply)

            return reply

        return pipeline


__all__ = ["Pathways"]
