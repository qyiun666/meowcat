# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat default organ stubs — no-op implementations satisfying Protocols.

Each Default* class extends Pluggable (v1.0.7), providing mount_plug / unmount_plug /
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
    DefaultAnomalyGrowth,
    DefaultCorrectionGrowth,
    DefaultCrystallizer,
    DefaultRoleEmergence,
)
from meowcat.defaults.organs.hippocampus import DefaultHippocampus
from meowcat.defaults.organs.sense import (
    DefaultEars,
    DefaultEyes,
    DefaultWhiskers,
)
from meowcat.defaults.organs.voice import (
    DefaultMouth,
    DefaultPaws,
    DefaultPurr,
    DefaultTail,
)

# Backward-compat / T-05 rename aliases: Noop* → Default*
DefaultAmygdala = NoopAmygdala
DefaultBrainstem = NoopBrainstem
DefaultCerebellum = NoopCerebellum
DefaultCerebrum = NoopCerebrum
DefaultCortex = NoopCortex
DefaultFrontal = NoopFrontal
DefaultHypothalamus = NoopHypothalamus
DefaultThalamus = NoopThalamus

__all__ = [
    # Brain
    "NoopThalamus", "DefaultThalamus",
    "NoopAmygdala", "DefaultAmygdala",
    "NoopFrontal", "DefaultFrontal",
    "NoopHypothalamus", "DefaultHypothalamus",
    "NoopCortex", "DefaultCortex",
    "NoopBrainstem", "DefaultBrainstem",
    "NoopCerebrum", "DefaultCerebrum",
    "NoopCerebellum", "DefaultCerebellum",
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
