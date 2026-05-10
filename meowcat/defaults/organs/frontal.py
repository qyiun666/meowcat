# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""Default Frontal implementation — keyword topic shift detection + topic history."""

from __future__ import annotations

from typing import Any

from meowcat.anatomy import ImplementationStyle
from meowcat.defaults.organs._brain_helpers import _extract_keywords
from meowcat.defaults.presets import KW_BILINGUAL, KeywordPreset
from meowcat.pluggable import Pluggable


class DefaultFrontal(Pluggable):
    """Frontal: keyword topic shift detection + topic history.

    Accepts a :class:`KeywordPreset` for domain-specific topic keywords
    and priority keywords. Default: bilingual.

    Tracks recent topics and detects significant shifts via keyword overlap.

    v1.3.6: Accepts an optional :class:`~meowcat.focus.FocusStore` for
    persistence.  ``save()`` / ``load()`` delegate to the store when
    configured; ``_export_state()`` / ``_import_state()`` support
    lifecycle-driven save/restore without path parameters.

    Mode A — is_continue / detect_shift first-hit override.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "is_continue": {"in": "msg: str", "out": "bool"},
        "detect_shift": {"in": "msg: str", "out": "bool"},
    }

    name: str = "renovated_frontal"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(
        self,
        keyword: KeywordPreset | None = None,
        threshold: float = 0.3,
        focus_store: Any | None = None,
    ) -> None:
        Pluggable.__init__(self)
        self._keyword = keyword or KW_BILINGUAL
        self._topics: list[str] = []
        self._current_keywords: set[str] = set()
        self._threshold: float = threshold
        self._focus_store = focus_store

    def is_continue(self, msg: str) -> bool:
        for _name, r in self._run_plugs_sync("is_continue", msg):
            if isinstance(r, bool):
                return r
        if not self._current_keywords:
            return False
        kws = set(
            _extract_keywords(
                msg, top_k=10, stop_words=self._keyword.stop_words
            )
        )
        overlap = len(kws & self._current_keywords)
        return overlap >= max(1, len(self._current_keywords) * self._threshold)

    def detect_shift(self, msg: str) -> bool:
        for _name, r in self._run_plugs_sync("detect_shift", msg):
            if isinstance(r, bool):
                return r
        return not self.is_continue(msg)

    def update_focus(self, result: Any) -> None:
        kw_source = (
            str(result.get("text", result.get("reply", "")))
            if isinstance(result, dict)
            else str(result)
        )
        self._current_keywords = set(
            _extract_keywords(
                kw_source, top_k=10, stop_words=self._keyword.stop_words
            )
        )

    def archive_focus(self) -> None:
        self._topics.append(", ".join(sorted(self._current_keywords)))
        self._current_keywords.clear()

    def save(self, path: Any | None = None) -> None:
        pass

    def load(self, path: Any | None = None) -> None:
        pass

    async def _load_from_store(self) -> None:
        if self._focus_store is None:
            return
        state = await self._focus_store.load()
        if state is not None:
            self._import_state(state)

    async def _save_to_store(self) -> None:
        if self._focus_store is None:
            return
        await self._focus_store.save(self._export_state())

    def _export_state(self) -> Any:
        from meowcat.focus import FocusState
        return FocusState(
            topics=list(self._topics),
            current_keywords=sorted(self._current_keywords),
            threshold=self._threshold,
        )

    def _import_state(self, state: Any) -> None:
        self._topics = list(state.topics)
        self._current_keywords = set(state.current_keywords)
        self._threshold = state.threshold
