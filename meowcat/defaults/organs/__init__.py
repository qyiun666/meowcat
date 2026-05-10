# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat default organ stubs — no-op implementations satisfying Protocols.

Each Noop* class extends Pluggable (v1.0.7), providing mount_plug / unmount_plug /
_run_plugs plugin capability. HOOKS class variable declares mountable hooks and their suggested signatures.

Three execution modes:
- A First-hit override: first non-default value is returned directly
- B Merge enhancement: all plugin results are merged into the default value
- C Full replacement: first plugin completely replaces default behavior
"""

from meowcat.defaults.organs.amygdala import NoopAmygdala
from meowcat.defaults.organs.brainstem import NoopBrainstem
from meowcat.defaults.organs.cerebellum import NoopCerebellum
from meowcat.defaults.organs.cerebrum import NoopCerebrum
from meowcat.defaults.organs.cortex import NoopCortex
from meowcat.defaults.organs.frontal import NoopFrontal
from meowcat.defaults.organs.hypothalamus import NoopHypothalamus
from meowcat.defaults.organs.thalamus import NoopThalamus
from meowcat.defaults.organs.growth import (
    NoopAnomalyGrowth,
    NoopCorrectionGrowth,
    NoopCrystallizer,
    NoopRoleEmergence,
)
from meowcat.defaults.organs.hippocampus import NoopHippocampus
from meowcat.defaults.organs.sense import (
    NoopEars,
    NoopEyes,
    NoopWhiskers,
)
from meowcat.defaults.organs.voice import (
    NoopMouth,
    NoopPaws,
    NoopPurr,
    NoopTail,
)

__all__ = [
    # Brain
    "NoopThalamus",
    "NoopAmygdala",
    "NoopFrontal",
    "NoopHypothalamus",
    "NoopCortex",
    "NoopBrainstem",
    "NoopCerebrum",
    "NoopCerebellum",
    "NoopHippocampus",
    # Senses
    "NoopEars",
    "NoopEyes",
    "NoopWhiskers",
    # Voice / Effectors
    "NoopMouth",
    "NoopPurr",
    "NoopTail",
    "NoopPaws",
    # Growth
    "NoopAnomalyGrowth",
    "NoopCorrectionGrowth",
    "NoopCrystallizer",
    "NoopRoleEmergence",
]
