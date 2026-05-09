# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat renovated organs — 简装修 (light-renovation) default implementations.

Each Renovated* class extends the Noop*毛坯 (bare) stub, adding minimal but
useful default behavior. Developers get a working cat out of the box with
``create_cat(renovated=True)``, and can opt-out per organ to use pure Noop*毛坯.

The renovated organs bridge the gap between pure stubs and full app-layer
implementations — enough to run simple flows, test wiring, and prototype.
"""

from meowcat.defaults.renovated.brain import (
    RenovatedAmygdala,
    RenovatedCortex,
    RenovatedFrontal,
    RenovatedHypothalamus,
    RenovatedThalamus,
)
from meowcat.defaults.renovated.brainstem import RenovatedBrainstem
from meowcat.defaults.renovated.cerebrum import (
    RenovatedCerebellum,
    RenovatedCerebrum,
)
from meowcat.defaults.renovated.growth import (
    RenovatedAnomalyGrowth,
    RenovatedCorrectionGrowth,
    RenovatedCrystallizer,
    RenovatedRoleEmergence,
)
from meowcat.defaults.renovated.hippocampus import RenovatedHippocampus
from meowcat.defaults.renovated.sense import (
    RenovatedEars,
    RenovatedEyes,
    RenovatedWhiskers,
)
from meowcat.defaults.renovated.voice import (
    RenovatedMouth,
    RenovatedPaws,
    RenovatedPurr,
    RenovatedTail,
)

# =========================================================================
# Organ name → renovated class mapping
# =========================================================================

RENOVATED_ORGAN_MAP: dict[str, type] = {
    # Brain
    "thalamus": RenovatedThalamus,
    "hippocampus": RenovatedHippocampus,
    "cerebrum": RenovatedCerebrum,
    "cerebellum": RenovatedCerebellum,
    "amygdala": RenovatedAmygdala,
    "frontal": RenovatedFrontal,
    "hypothalamus": RenovatedHypothalamus,
    "cortex": RenovatedCortex,
    "brainstem": RenovatedBrainstem,
    # Senses
    "ears": RenovatedEars,
    "eyes": RenovatedEyes,
    "whiskers": RenovatedWhiskers,
    "paws": RenovatedPaws,
    # Voice
    "mouth": RenovatedMouth,
    "purr": RenovatedPurr,
    "tail": RenovatedTail,
    # Growth
    "anomaly_growth": RenovatedAnomalyGrowth,
    "correction_growth": RenovatedCorrectionGrowth,
    "crystallizer": RenovatedCrystallizer,
    "role_emergence": RenovatedRoleEmergence,
}


__all__ = [
    # Brain
    "RenovatedThalamus",
    "RenovatedHippocampus",
    "RenovatedCerebrum",
    "RenovatedCerebellum",
    "RenovatedAmygdala",
    "RenovatedFrontal",
    "RenovatedHypothalamus",
    "RenovatedCortex",
    "RenovatedBrainstem",
    # Senses
    "RenovatedEars",
    "RenovatedEyes",
    "RenovatedWhiskers",
    "RenovatedPaws",
    # Voice
    "RenovatedMouth",
    "RenovatedPurr",
    "RenovatedTail",
    # Growth
    "RenovatedAnomalyGrowth",
    "RenovatedCorrectionGrowth",
    "RenovatedCrystallizer",
    "RenovatedRoleEmergence",
    # Mappings
    "RENOVATED_ORGAN_MAP",
]
