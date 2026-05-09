# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat Colony — LLM shelf Mixin (v1.3.9: extracted from colony/__init__.py)."""

from __future__ import annotations

from typing import Any

from meowcat.assembly import CatBase
from meowcat.models import ModelConfig


class _LLMShelfMixin:
    """LLM shelf management methods extracted from Colony.

    Provides LLM model storage/retrieval (stock_llm, unstock_llm, pick_llm,
    llm_shelf) and cat assembly with automatic LLM picking (assemble_cat).

    Requires the host class to provide:
        - ``self._llm_shelf`` (dict of name -> ModelConfig)
        - ``self._run_plugs_sync`` (Pluggable plugin executor)
        - ``self.create_cat()`` (from _CatOpsMixin)
    """

    # -- LLM shelf (v1.1.5) -------------------------------------------

    @property
    def llm_shelf(self) -> dict[str, ModelConfig]:
        """Read-only copy of the shared LLM shelf."""
        return dict(self._llm_shelf)  # type: ignore[attr-defined]

    def stock_llm(self, name: str, config: ModelConfig) -> None:
        """Stock a new LLM config on the shelf (overwrite if exists)."""
        self._llm_shelf[name] = config  # type: ignore[attr-defined]

    def unstock_llm(self, name: str) -> bool:
        """Remove an LLM from the shelf. Returns True if removed."""
        return self._llm_shelf.pop(name, None) is not None  # type: ignore[attr-defined]

    def pick_llm(self, name: str | None = None) -> ModelConfig:
        """Pick an LLM config from the shelf with cascade fallback.

        Cascade order:
        1. Named lookup — ``pick_llm("smart")``
        2. First available — ``pick_llm()`` returns any entry
        3. Plugin hook — ``on_pick`` plugin can override (first-hit)

        Raises:
            ValueError: Shelf is empty and no name specified.
            KeyError: Named LLM not found on shelf.
        """
        # Plugin hook (first-hit)
        # type: ignore[attr-defined]
        for _hook, r in self._run_plugs_sync("on_pick", name, dict(self._llm_shelf)):
            if isinstance(r, ModelConfig):
                return r

        if name is not None:
            if name not in self._llm_shelf:  # type: ignore[attr-defined]
                raise KeyError(
                    # type: ignore[attr-defined]
                    f"LLM '{name}' not found on shelf. Available: {list(self._llm_shelf.keys())}"
                )
            return self._llm_shelf[name]  # type: ignore[attr-defined]

        if not self._llm_shelf:  # type: ignore[attr-defined]
            raise ValueError(
                # type: ignore[attr-defined]
                f"LLM shelf is empty in colony '{self.colony_id}'. "
                f"Stock at least one LLM or pass llm=... explicitly."
            )
        # type: ignore[attr-defined]
        return next(iter(self._llm_shelf.values()))

    def assemble_cat(
        self,
        *,
        name: str | None = None,
        llm: str | ModelConfig | None = None,
        parent_id: str | None = None,
        allowed_organs: frozenset[str] | None = None,
        memory_snapshot: dict | None = None,
        **cat_kwargs: Any,
    ) -> CatBase:
        """Create a cat with LLM picked from shelf (or own config).

        LLM resolution order:
        1. ``llm=ModelConfig(...)`` — cat brings its own LLM
        2. ``llm="smart"`` — pick named LLM from shelf
        3. ``llm=None`` — pick first available from shelf

        Args:
            name: Optional display name (defaults to cat_uid).
            llm: LLM config or shelf name. None = auto-pick from shelf.
            parent_id: Parent cat identifier.
            allowed_organs: Organ access allowlist.
            memory_snapshot: Context slice assigned by parent cat.
            **cat_kwargs: Additional arguments passed to CatBase.

        Returns:
            Registered CatBase instance with ``_llm_config`` attribute.
        """
        llm_config = llm if isinstance(
            llm, ModelConfig) else self.pick_llm(llm)

        cat = self.create_cat(  # type: ignore[attr-defined]
            name=name,
            parent_id=parent_id,
            allowed_organs=allowed_organs,
            memory_snapshot=memory_snapshot,
            **cat_kwargs,
        )
        cat._llm_config = llm_config  # type: ignore[attr-defined]
        return cat
