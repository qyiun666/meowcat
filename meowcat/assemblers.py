# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat assembly helpers — ``mount_known_organs`` and ``assemble_default_cat``.

Extracted from ``assembly.py`` (v1.3.9) to keep each file ≤500 lines.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from meowcat.assembly import CatBase

from meowcat.reflex import Reflex


def mount_known_organs(cat: CatBase) -> None:
    """Scan known organ attributes on cat and mount to OrganHost.

    Covers brain / sense / voice / growth four core organ categories.
    Shared by ``factory.create_cat()`` and ``assemble_default_cat()``
    to eliminate duplicate organ name lists.

    Args:
        cat: CatBase instance with organ attributes already set
    """
    _BRAIN_NAMES = {  # noqa: N806
        "hippocampus",
        "thalamus",
        "amygdala",
        "frontal",
        "hypothalamus",
        "cerebellum",
        "cerebrum",
        "brainstem",
        "cortex",
    }
    _SENSE_NAMES = {"ears", "eyes", "whiskers", "paws"}  # noqa: N806
    _VOICE_NAMES = {"mouth", "purr", "tail"}  # noqa: N806
    _GROWTH_NAMES = {  # noqa: N806
        "anomaly_growth",
        "correction_growth",
        "crystallizer",
        "role_emergence",
    }

    for name in _BRAIN_NAMES:
        organ = getattr(cat, name, None)
        if organ is not None:
            cat.mount("brain", name, organ)

    for name in _SENSE_NAMES:
        organ = getattr(cat, name, None)
        if organ is not None:
            cat.mount("sense", name, organ)

    for name in _VOICE_NAMES:
        organ = getattr(cat, name, None)
        if organ is not None:
            cat.mount("voice", name, organ)

    for name in _GROWTH_NAMES:
        organ = getattr(cat, name, None)
        if organ is not None:
            cat.mount("growth", name, organ)

    # v1.2.36: Notify that organs are mounted — hooks can now access organs
    cat._notify_organs_mounted()


# -- Top-level assembly function (v0.5.9 added) ------------------------------


def assemble_default_cat(
    cat: CatBase,
    *,
    reflex_stages: list[Any] | None = None,
    reflexes: list[Reflex] | None = None,
) -> None:
    """One-click assemble default cat: scan organ attrs → mount → wire →
    register reflex.

    v0.5.21: No longer calls freeze_nervous_system(); caller controls freeze
    timing. The caller can freeze after wiring + reflex registration
    completes.

    Flow:

    1. Scan known organ attribute names on ``cat`` and ``mount`` to host
    2. ``cat.wire_default_nervous_system()`` assemble biological defaults
    3. Register reflexes (provided by caller)

    Args:
        cat: CatBase instance with organ attributes set
        reflex_stages: Stage list for default text_dialogue reflex
            (only effective when ``reflexes`` contains text_dialogue)
        reflexes: Reflex list; ``None`` means register no reflexes
    """
    mount_known_organs(cat)
    cat.wire_default_nervous_system()

    # Builtin tools (v2.0: moved to application layer, removed BUILTIN_TOOLS
    # registration. Application layer should register tools via cat.tool_registry.register().)

    # Reflexes (caller-provided)
    if reflexes:
        for ref in reflexes:
            # If reflex_stages are provided and it's text_dialogue, inject stages
            if ref.name == "text_dialogue" and reflex_stages is not None:
                ref = Reflex(
                    name=ref.name,
                    trigger=ref.trigger,
                    path=ref.path,
                    priority=ref.priority,
                    stages=list(reflex_stages),
                )
            cat.register_reflex(ref)


__all__ = ["mount_known_organs", "assemble_default_cat"]
