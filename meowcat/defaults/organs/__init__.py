# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat default organ stubs — default implementations satisfying Protocols.

Each Default* class extends Pluggable (v1.0.7), providing mount_plug / unmount_plug /
_run_plugs plugin capability. HOOKS class variable declares mountable hooks and their suggested signatures.

Three execution modes:
- A First-hit override: first non-default value is returned directly
- B Merge enhancement: all plugin results are merged into the default value
- C Full replacement: first plugin completely replaces default behavior
"""

from meowcat.defaults.organs.amygdala import DefaultAmygdala
from meowcat.defaults.organs.brainstem import DefaultBrainstem
from meowcat.defaults.organs.cerebellum import DefaultCerebellum
from meowcat.defaults.organs.cerebrum import DefaultCerebrum
from meowcat.defaults.organs.cortex import DefaultCortex
from meowcat.defaults.organs.frontal import DefaultFrontal
from meowcat.defaults.organs.growth import (
    DefaultAnomalyGrowth,
    DefaultCorrectionGrowth,
    DefaultCrystallizer,
    DefaultRoleEmergence,
)
from meowcat.defaults.organs.hippocampus import DefaultHippocampus
from meowcat.defaults.organs.hypothalamus import DefaultHypothalamus
from meowcat.defaults.organs.sense import (
    DefaultEars,
    DefaultEyes,
    DefaultWhiskers,
)
from meowcat.defaults.organs.thalamus import DefaultThalamus
from meowcat.defaults.organs.voice import (
    DefaultMouth,
    DefaultPaws,
    DefaultPurr,
    DefaultTail,
)

__all__ = [
    # Brain
    "DefaultThalamus",
    "DefaultAmygdala",
    "DefaultFrontal",
    "DefaultHypothalamus",
    "DefaultCortex",
    "DefaultBrainstem",
    "DefaultCerebrum",
    "DefaultCerebellum",
    "DefaultHippocampus",
    # Senses
    "DefaultEars",
    "DefaultEyes",
    "DefaultWhiskers",
    # Voice / Effectors
    "DefaultMouth",
    "DefaultPurr",
    "DefaultTail",
    "DefaultPaws",
    # Growth
    "DefaultAnomalyGrowth",
    "DefaultCorrectionGrowth",
    "DefaultCrystallizer",
    "DefaultRoleEmergence",
]
