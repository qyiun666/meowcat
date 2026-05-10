# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""Backward-compatible re-exports from split organ modules.

The original brain.py (990 lines) has been split into individual organ files
as part of v2.3.0 cleanup (H-05). This module re-exports everything
for callers that import directly from ``defaults.organs.brain``.

Prefer importing from ``meowcat.defaults.organs`` directly.
"""

from meowcat.defaults.organs.amygdala import DefaultAmygdala
from meowcat.defaults.organs.brainstem import DefaultBrainstem
from meowcat.defaults.organs.cerebellum import DefaultCerebellum
from meowcat.defaults.organs.cerebrum import DefaultCerebrum
from meowcat.defaults.organs.cortex import DefaultCortex
from meowcat.defaults.organs.frontal import DefaultFrontal
from meowcat.defaults.organs.hypothalamus import DefaultHypothalamus
from meowcat.defaults.organs.thalamus import DefaultThalamus

__all__ = [
    "DefaultThalamus",
    "DefaultAmygdala",
    "DefaultFrontal",
    "DefaultHypothalamus",
    "DefaultCortex",
    "DefaultBrainstem",
    "DefaultCerebrum",
    "DefaultCerebellum",
]
