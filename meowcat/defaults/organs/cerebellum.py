# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""Default Cerebellum implementation — callable-based fast-response adapter."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from meowcat.anatomy import ImplementationStyle
from meowcat.defaults.presets import OrganPrompt, PromptPreset
from meowcat.pluggable import Pluggable


class NoopCerebellum(Pluggable):
    """Cerebellum: callable-based fast-response adapter with prompt preset.

    Same pattern as NoopCerebrum — accepts optional ``llm_fn``,
    :class:`PromptPreset`, and :class:`OrganPrompt`.

    Mode C — generate / stream_generate full replacement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "generate": {
            "in": "prompt: str, system_prompt: str|None, temperature: float, max_tokens: int|None",
            "out": "str",
        },
        "stream_generate": {
            "in": "prompt: str, system_prompt: str|None, temperature: float, max_tokens: int|None",
            "out": "AsyncIterator[str]",
        },
    }

    name: str = "renovated_cerebellum"
    impl_style: ImplementationStyle = ImplementationStyle.MODEL

    def __init__(
        self,
        llm_fn: Callable[..., Awaitable[str]
                         ] | Callable[..., str] | None = None,
        default_model: str = "renovated",
        prompt: PromptPreset | None = None,
        organ_prompt: OrganPrompt | None = None,
    ) -> None:
        Pluggable.__init__(self)
        self._llm_fn = llm_fn
        self._model = default_model
        self._prompt = prompt
        self._organ_prompt = organ_prompt

    @property
    def organ_prompt(self) -> OrganPrompt | None:
        """Per-organ prompt slot (v1.3.6)."""
        return self._organ_prompt

    def diagnose(self) -> dict[str, Any]:
        return {
            "model": self._model,
            "has_llm": self._llm_fn is not None,
            "prompt_preset": self._prompt.name if self._prompt else "none",
            "organ_prompt": self._organ_prompt is not None,
        }

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        async for _name, r in self._run_plugs(
            "generate", prompt, system_prompt, temperature, max_tokens
        ):
            if isinstance(r, str):
                return r

        # RuleSet injection (v2.1.0 — fallback: inject even when Brainstem is bypassed)
        if system_prompt:
            host = getattr(self, "_organ_host", None)
            if host is not None:
                cat = getattr(host, "_cat", None)
                if cat is not None and cat.rule_set is not None:
                    rule_block = cat.rule_set.render(route="tool_use")
                    if rule_block:
                        system_prompt = f"{system_prompt}\n\n{rule_block}"

        if self._llm_fn is not None:
            import inspect

            result = self._llm_fn(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if inspect.isawaitable(result):
                result = await result
            return str(result)
        return "(renovated cerebellum: no LLM configured)"

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> Any:
        async for _name, r in self._run_plugs(
            "stream_generate", prompt, system_prompt, temperature, max_tokens
        ):
            return r
        result = await self.generate(
            prompt, system_prompt, temperature, max_tokens
        )

        async def _stream():
            yield result

        return _stream()

    def reload_config(self) -> None:
        pass
