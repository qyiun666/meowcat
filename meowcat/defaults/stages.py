# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat default Stage stubs — default pipeline stage implementations (v1.0.17).

Each Default*Stage extends BaseStage and provides a default name derived from its
class name. Applications subclass and override :meth:`run()` with real logic;
unused Stages stay as no-op pass-through.

Factory ``build_default_pipeline()`` returns a minimal Pipeline with common
conversation Stages in order.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from meowcat.models import PipelineContext, StageEvent

from meowcat.pluggable import Pluggable


class BaseStage(Pluggable):
    """Pipeline Stage base class — every Stage inherits from this.

    :attr:`name` is derived automatically from the class name
    (e.g. ``DefaultLocateStage`` → ``"default_locate"``).
    Default :meth:`run` is a no-op async generator (yields nothing).

    HOOKS declares the ``run`` hook for documentation;
    applications mount plugins via ``mount_plug("run", ...)``
    but the Stage subclass owns the actual ``run()`` dispatch.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "run": {"in": "ctx: PipelineContext", "out": "AsyncIterator[StageEvent]"},
    }

    def __init__(self) -> None:
        Pluggable.__init__(self)
        cls_name = type(self).__name__
        if cls_name.startswith("Default"):
            cls_name = cls_name[7:]
        # CamelCase → snake_case
        import re

        self.name = "default_" + \
            re.sub(r"(?<!^)(?=[A-Z])", "_", cls_name).lower()

    def diagnose(self) -> dict[str, Any]:
        return {}

    async def run(self, ctx: PipelineContext) -> AsyncIterator[StageEvent]:
        """Default no-op: yields nothing. Override in subclass."""
        if False:
            yield


# -- Default Stage stubs -----------------------------------------------


class DefaultIngestStage(BaseStage):
    """Default input preprocessing Stage."""


class DefaultLocateStage(BaseStage):
    """Default memory retrieval Stage."""


class DefaultRouteStage(BaseStage):
    """Default routing decision Stage."""


class DefaultExecuteStage(BaseStage):
    """Default LLM execution Stage."""


class DefaultPostStage(BaseStage):
    """Default post-processing (memory write) Stage."""


class DefaultCompressStage(BaseStage):
    """Default context compression Stage."""


# -- Default pipeline factory -----------------------------------------


def build_default_pipeline() -> list[BaseStage]:
    """Return a default conversation Stage sequence for :class:`Pipeline`.

    Returns:
        ``[Ingest, Locate, Route, Execute, Post]`` — a minimal
        conversation pipeline. Applications override individual
        Stages or reorder/replace as needed.
    """
    return [
        DefaultIngestStage(),
        DefaultLocateStage(),
        DefaultRouteStage(),
        DefaultExecuteStage(),
        DefaultPostStage(),
    ]


__all__ = [
    "BaseStage",
    "DefaultIngestStage",
    "DefaultLocateStage",
    "DefaultRouteStage",
    "DefaultExecuteStage",
    "DefaultPostStage",
    "DefaultCompressStage",
    "build_default_pipeline",
]
