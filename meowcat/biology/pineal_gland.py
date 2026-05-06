# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""PinealGland — the cat's insight organ: scribbles → meditation → insights.

插座式设计: framework provides ``meditate()`` algorithm + ``trigger()`` entry,
app-layer decides WHEN to trigger and HOW to fuse insights.

Usage::

    from meowcat.biology.pineal_gland import PinealGland
    from meowcat.biology.scribble_pad import ScribblePad
    from meowcat.biology.fusion_cycle import FusionCycle

    pad = ScribblePad(capacity=100)
    gland = PinealGland(pad)

    # App-layer defines fusion targets
    def my_fuse_self(insights):
        cat.cortex.remember_many(insights)
    def my_fuse_colony(insights):
        colony.storage_set("knowledge", "insights", insights)

    gland.on_fuse_self = my_fuse_self
    gland.on_fuse_colony = my_fuse_colony

    # Trigger strategies
    gland.trigger()                           # immediate
    gland.trigger_if(FusionCycle.on_full(50))  # only when full
    gland.trigger_if(FusionCycle.on_event("conversation_end"))
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TYPE_CHECKING

from meowcat.log import MeowLog
from meowcat.events import FusionEvent
from meowcat.pluggable import Pluggable

if TYPE_CHECKING:
    from meowcat.biology.scribble_pad import ScribblePad

_log = MeowLog.get("meowcat.pineal_gland")


class Insight:
    """A single insight distilled from scribble fragments.

    Attributes:
        summary: Condensed insight text.
        confidence: 0.0-1.0 confidence score from the merger.
        source_count: How many fragments contributed to this insight.
        contradictions: List of contradictory insight texts found during meditation.
        tags: Optional topic tags for categorisation.
    """

    __slots__ = ("summary", "confidence", "source_count",
                 "contradictions", "tags")

    def __init__(
        self,
        summary: str,
        confidence: float = 0.5,
        source_count: int = 1,
        contradictions: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> None:
        self.summary = summary
        self.confidence = confidence
        self.source_count = source_count
        self.contradictions = contradictions or []
        self.tags = tags or []

    def __repr__(self) -> str:
        return (
            f"Insight(summary={self.summary!r}, confidence={self.confidence:.2f}, "
            f"source_count={self.source_count}, tags={self.tags})"
        )


class PinealGland(Pluggable):
    """Cat's insight organ — distills scribble fragments into insights.

    Framework layer responsibilities:
    - ``meditate()`` pipeline: merge → contradiction → filter (all pluggable)
    - ``trigger()`` / ``trigger_if()`` entry points
    - ``fuse_to_self()`` / ``fuse_to_colony()`` hooks

    App layer responsibilities:
    - When to call ``trigger()`` (every turn? timer? event?)
    - What ``on_fuse_self`` / ``on_fuse_colony`` do (write to Cortex / SharedStorage)

    Args:
        scribble_pad: The cat's ScribblePad to drain fragments from.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "merger": {"in": "scribbles: list[Any]", "out": "list[Insight]"},
        "contradiction": {"in": "insights: list[Insight]", "out": "list[tuple[int,int]]"},
        "filter": {"in": "insight: Insight", "out": "bool | None"},
    }

    __slots__ = ("_pad", "_on_fuse_self", "_on_fuse_colony")

    def __init__(self, scribble_pad: ScribblePad) -> None:
        super().__init__()
        self._pad = scribble_pad
        self._on_fuse_self: Callable[[list[Insight]], None] | None = None
        self._on_fuse_colony: Callable[[list[Insight]], None] | None = None

    # -- Fusion target hooks (set by app layer) -------------------------

    @property
    def on_fuse_self(self) -> Callable[[list[Insight]], None] | None:
        """App-layer callback: fuse insights into cat's own self (Cortex, etc.)."""
        return self._on_fuse_self

    @on_fuse_self.setter
    def on_fuse_self(self, fn: Callable[[list[Insight]], None] | None) -> None:
        self._on_fuse_self = fn

    @property
    def on_fuse_colony(self) -> Callable[[list[Insight]], None] | None:
        """App-layer callback: fuse insights into colony shared knowledge."""
        return self._on_fuse_colony

    @on_fuse_colony.setter
    def on_fuse_colony(self, fn: Callable[[list[Insight]], None] | None) -> None:
        self._on_fuse_colony = fn

    # -- Core API ------------------------------------------------------

    def meditate(self, scribbles: list[Any]) -> list[Insight]:
        """Distill scribble fragments into insights.

        Pipeline: merger → contradiction → filter (all pluggable).

        Args:
            scribbles: Raw fragments drained from ScribblePad.

        Returns:
            Filtered list of Insight objects.
        """
        if not scribbles:
            return []

        # 1. Merger: group and summarise fragments into insights
        insights = self._run_merger(scribbles)

        # 2. Contradiction: detect conflicting insights
        contradiction_pairs: list[tuple[int, int]] = []
        for _name, r in self._run_plugs_sync("contradiction", list(insights)):
            if isinstance(r, list):
                contradiction_pairs = r
# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT


        # Mark contradictions on insights
        for i_idx, j_idx in contradiction_pairs:
            if i_idx < len(insights) and j_idx < len(insights):
                insights[i_idx].contradictions.append(insights[j_idx].summary)
                insights[j_idx].contradictions.append(insights[i_idx].summary)

        # 3. Filter: drop low-quality insights
        filtered: list[Insight] = []
        for ins in insights:
            keep = True
            for _name, ok in self._run_plugs_sync("filter", ins):
                if ok is False:
                    keep = False
                    break
            if keep:
                filtered.append(ins)

        _log.info("meditate", scribbles_in=len(
            scribbles), insights_out=len(filtered))
        return filtered

    def fuse_to_self(self, insights: list[Insight]) -> None:
        """Fuse insights into cat's own self (delegates to app-layer callback).

        Args:
            insights: Insights from ``meditate()``.
        """
        if self._on_fuse_self and insights:
            self._on_fuse_self(insights)
            _log.info(FusionEvent.FUSE_SELF, count=len(insights))
            _log.debug("fuse_to_self", count=len(insights))

    def fuse_to_colony(self, insights: list[Insight]) -> None:
        """Fuse insights into colony shared knowledge (delegates to app-layer callback).

        Args:
            insights: Insights from ``meditate()``.
        """
        if self._on_fuse_colony and insights:
            self._on_fuse_colony(insights)
            _log.info(FusionEvent.FUSE_COLONY, count=len(insights))
            _log.debug("fuse_to_colony", count=len(insights))

    def trigger(
        self,
        *,
        fuse_self: bool = True,
        fuse_colony: bool = True,
    ) -> list[Insight]:
        """Immediate trigger: drain ScribblePad → meditate → fuse.

        Args:
            fuse_self: Whether to fuse insights into cat's own self.
            fuse_colony: Whether to fuse insights into colony shared knowledge.

        Returns:
            The insights produced (empty list if nothing to fuse).
        """
        _log.info(FusionEvent.TRIGGER_START)
        scribbles = self._pad.drain()
        if not scribbles:
            _log.debug("trigger skipped (empty pad)")
            _log.info(FusionEvent.TRIGGER_END, insights_count=0)
            return []

        insights = self.meditate(scribbles)
        if insights:
            if fuse_self:
                self.fuse_to_self(insights)
            if fuse_colony:
                self.fuse_to_colony(insights)

        _log.info(FusionEvent.TRIGGER_END, insights_count=len(insights),
                  scribbles=len(scribbles))
        _log.info("trigger", scribbles=len(scribbles), insights=len(insights),
                  fuse_self=fuse_self, fuse_colony=fuse_colony)
        return insights

    def trigger_if(
        self,
        condition: Callable[[ScribblePad], bool],
        *,
        fuse_self: bool = True,
        fuse_colony: bool = True,
    ) -> list[Insight]:
        """Conditional trigger: only execute if *condition* evaluates True.

        Args:
            condition: Callable that receives the ScribblePad and returns bool.
            fuse_self: Whether to fuse insights into cat's own self.
            fuse_colony: Whether to fuse insights into colony shared knowledge.

        Returns:
            Insights if triggered, empty list otherwise.
        """
        if condition(self._pad):
            return self.trigger(fuse_self=fuse_self, fuse_colony=fuse_colony)
        return []

    def diagnose(self) -> dict[str, Any]:
        """Return a diagnostic snapshot."""
        return {
            "pad_count": self._pad.count(),
            "pad_capacity": self._pad.capacity,
            "pad_is_full": self._pad.is_full(),
            "has_fuse_self": self._on_fuse_self is not None,
            "has_fuse_colony": self._on_fuse_colony is not None,
            "plugs": self.list_plugs(),
        }

    # -- Internal -------------------------------------------------------

    def _run_merger(self, scribbles: list[Any]) -> list[Insight]:
        """Run merger plugins; fallback to DefaultMerger if none registered."""
        results: list[Insight] = []
        for _name, r in self._run_plugs_sync("merger", scribbles):
            if isinstance(r, list):
                results = r
        if results:
            return results
        # Fallback: DefaultMerger
        return _default_merger(scribbles)


# -- Prefabs (开箱即用，可替换) ------------------------------------------


def _default_merger(
    scribbles: list[Any],
    *,
    jaccard_threshold: float = 0.3,
) -> list[Insight]:
    """Default merger: group by keyword Jaccard similarity.

    Converts each scribble to a string, computes keyword overlap, and groups
    similar fragments into a single Insight.

    Args:
        scribbles: Raw fragments from ScribblePad.
        jaccard_threshold: Minimum Jaccard similarity to group fragments.
    """
    if not scribbles:
        return []

# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

    def _to_keywords(item: Any) -> set[str]:
        s = str(item) if not isinstance(item, str) else item
        # Simple word tokenisation
        return set(s.lower().split())

    groups: list[list[Any]] = []
    used: set[int] = set()

    for i, item in enumerate(scribbles):
        if i in used:
            continue
        group = [item]
        used.add(i)
        ki = _to_keywords(item)
        if not ki:
            continue
        for j in range(i + 1, len(scribbles)):
            if j in used:
                continue
            kj = _to_keywords(scribbles[j])
            if not kj:
                continue
            intersection = len(ki & kj)
            union = len(ki | kj)
            jaccard = intersection / union if union > 0 else 0.0
            if jaccard >= jaccard_threshold:
                group.append(scribbles[j])
                used.add(j)
        groups.append(group)

    insights: list[Insight] = []
    for group in groups:
        texts = [str(g)[:200] for g in group]
        summary = " | ".join(texts[:3])  # merge up to 3 representative texts
        if len(texts) > 3:
            summary += f" ... (+{len(texts) - 3})"
        insights.append(Insight(
            summary=summary,
            confidence=min(0.9, 0.5 + 0.1 * len(group)),
            source_count=len(group),
        ))
    return insights


class DefaultMerger:
    """Default merger plugin: keyword Jaccard similarity grouping.

    Args:
        jaccard_threshold: Minimum Jaccard similarity to group fragments
            (default 0.3).

    Usage::

        gland.plug("merger", DefaultMerger(jaccard_threshold=0.5))
    """

    def __init__(self, jaccard_threshold: float = 0.3) -> None:
        self._threshold = jaccard_threshold

    def __call__(self, scribbles: list[Any]) -> list[Insight]:
        return _default_merger(scribbles, jaccard_threshold=self._threshold)


_DEFAULT_ANTONYMS: tuple[tuple[str, str], ...] = (
    ("good", "bad"), ("success", "failure"), ("safe", "dangerous"),
    ("fast", "slow"), ("easy", "hard"), ("correct", "wrong"),
    ("true", "false"), ("yes", "no"), ("allow", "deny"),
    ("approve", "reject"), ("open", "closed"), ("high", "low"),
)


class DefaultContradiction:
    """Default contradiction detector: flag insights with opposite keywords.

    Detects simple semantic opposition via keyword antonym pairs
    (e.g. "good"/"bad", "success"/"failure").

    Args:
        antonyms: Optional custom antonym pairs to replace the defaults.

    Usage::

        gland.plug("contradiction", DefaultContradiction())
        gland.plug("contradiction",
                    DefaultContradiction(antonyms=(("yes", "no"),)))
    """

    def __init__(
        self,
        antonyms: tuple[tuple[str, str], ...] | None = None,
    ) -> None:
        self._antonyms = antonyms if antonyms is not None else _DEFAULT_ANTONYMS

    def __call__(self, insights: list[Insight]) -> list[tuple[int, int]]:
        pairs: list[tuple[int, int]] = []
        for i in range(len(insights)):
            si = insights[i].summary.lower()
            for j in range(i + 1, len(insights)):
                sj = insights[j].summary.lower()
                for pos, neg in self._antonyms:
                    if pos in si and neg in sj:
                        pairs.append((i, j))
                        break
                    if neg in si and pos in sj:
                        pairs.append((i, j))
                        break
        return pairs


class DefaultInsightFilter:
    """Default insight filter: drop too-short or near-duplicate insights.

    Drops insights whose summary is shorter than *min_len* (default 5 chars)
    or whose summary text is a substring of another insight's summary.

    Usage::

        gland.plug("filter", DefaultInsightFilter(min_len=10))
    """

    def __init__(self, min_len: int = 5) -> None:
        self._min_len = min_len

    def __call__(self, insight: Insight) -> bool | None:
        if len(insight.summary) < self._min_len:
            return False
        return None


__all__ = [
    "Insight",
    "PinealGland",
    "DefaultMerger",
    "DefaultContradiction",
    "DefaultInsightFilter",
]

