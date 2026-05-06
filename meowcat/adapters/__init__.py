# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat organ adapters — plug external agents / skills into organ sockets.

v1.2.14: Each organ Protocol is a socket; any external agent or skill can be the plug.
``AgentOrgan`` and ``SkillOrgan`` base classes provide delegation, error wrapping,
and Pluggable compatibility — subclasses only declare the method mapping.

Usage::

    from meowcat.adapters import CerebrumAgent, HippocampusAgent

    cat.mount("brain", "cerebrum", CerebrumAgent(my_coding_agent))
    cat.mount("brain", "hippocampus", HippocampusAgent(my_memory_skill))
"""

from meowcat.adapters.base import AgentOrgan, SkillOrgan
from meowcat.adapters.brain import (
    AmygdalaAgent,
    BrainstemAgent,
    CerebellumAgent,
    CerebrumAgent,
    CortexAgent,
    FrontalAgent,
    HippocampusAgent,
    HypothalamusAgent,
    ThalamusAgent,
)
from meowcat.adapters.sense import (
    EarsAgent,
    EyesAgent,
    PawsAgent,
    WhiskersAgent,
)
from meowcat.adapters.voice import (
    MouthAgent,
    PurrAgent,
    TailAgent,
)
# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT


__all__ = [
    "AgentOrgan",
    "SkillOrgan",
    # Brain
    "CerebrumAgent",
    "CerebellumAgent",
    "ThalamusAgent",
    "HippocampusAgent",
    "AmygdalaAgent",
    "BrainstemAgent",
    "FrontalAgent",
    "HypothalamusAgent",
    "CortexAgent",
    # Sense
    "EarsAgent",
    "EyesAgent",
    "WhiskersAgent",
    "PawsAgent",
    # Voice
    "MouthAgent",
    "PurrAgent",
    "TailAgent",
]

