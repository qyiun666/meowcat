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

from meowcat.defaults.organs.brain import (
    NoopAmygdala,
    NoopBrainstem,
    NoopCerebellum,
    NoopCerebrum,
    NoopCortex,
    NoopFrontal,
    NoopHippocampus,
    NoopHypothalamus,
    NoopThalamus,
)
from meowcat.defaults.organs.growth import (
    NoopAnomalyGrowth,
    NoopCorrectionGrowth,
    NoopCrystallizer,
    NoopRoleEmergence,
)
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
