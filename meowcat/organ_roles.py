# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat organ role declaration table — immutable organ purpose descriptions.

Each organ registers a one-sentence description of its core responsibility.
This file has zero business logic, only declarations, does not change any code behavior.
When adding/removing organs, update this table accordingly.

This file has zero third-party dependencies, zero meowagent imports.
"""


from __future__ import annotations

from typing import Final

from meowcat.anatomy import (
    AMYGDALA,
    ANOMALY_GROWTH,
    BRAINSTEM,
    CEREBELLUM,
    CEREBRUM,
    CORRECTION_GROWTH,
    CORTEX,
    CRYSTALLIZER,
    EARS,
    EYES,
    FRONTAL,
    HIPPOCAMPUS,
    HYPOTHALAMUS,
    MOUTH,
    PAWS,
    PURR,
    ROLE_EMERGENCE,
    TAIL,
    THALAMUS,
    WHISKERS,
)
from meowcat.wiring import Organ

ORGAN_ROLES: Final[dict[Organ, str]] = {
    # -- Brain regions --
    THALAMUS: "Route decision — all input passes through me first, determine whether to go to cerebrum or cerebellum",
    HIPPOCAMPUS: "Memory access — the single entry point for storing, finding, and forgetting",
    CEREBRUM: "Deep reasoning — invokes LLM for complex thinking",
    CEREBELLUM: "Fast response — pattern matching + sole upstream for all effectors",
    AMYGDALA: "Safety review — danger detection + risk assessment",
    FRONTAL: "Focus/Planning — current topic management + task decomposition",
    HYPOTHALAMUS: "Self-maintenance — memory decay + orphan data cleanup",
    CORTEX: "Worldview — distill cognition and self-awareness from experience",
    BRAINSTEM: "Coordination hub — lifecycle + flow orchestration (does not own data)",
    # -- Senses --
    EARS: "Text input — CLI/API/Discord/Telegram",
    EYES: "Visual input — images/video",
    WHISKERS: "Environment sensing — browser + I/O anomaly detection",
    PAWS: "Tool execution — the single execution entry for Skill/MCP/commands",
    # -- Voice --
    MOUTH: "Voice output — TTS + text reply",
    PURR: "Streaming status — streaming progress",
    TAIL: "Status bar — CLI status signal",
    # -- Growth (v0.5.15 Loop C) --
    ANOMALY_GROWTH: "Anomaly sedimentation — user-flagged anomaly patterns written to persistent graph",
    CORRECTION_GROWTH: "Correction solidification — user-corrected erroneous facts written as permanent fixes",
    CRYSTALLIZER: "Experience crystallization — accumulated usage crystallizes into reusable skills",
    ROLE_EMERGENCE: "Role emergence — evolve role behavior patterns from interactions",
}

__all__ = ["ORGAN_ROLES"]

