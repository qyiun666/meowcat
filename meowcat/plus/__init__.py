# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat plus — optional pluggable module pack.

Install with ``pip install meowcat[plus]`` to pull in runtime dependencies
(chromadb).  Pure-framework users get zero I/O imports
because everything in ``meowcat/plus/`` is only loaded on demand.

See :ref:`meowcat-plus-architecture`.
"""

from __future__ import annotations

from meowcat.plus.chroma_store import ChromaStore
from meowcat.plus.crystallizer import Crystallizer, DefaultDetector
from meowcat.plus.persona_loader import PersonaLoader
from meowcat.plus.skill_loader import SkillLoader

__all__ = [
    "ChromaStore",
    "SkillLoader",
    "PersonaLoader",
    "Crystallizer",
    "DefaultDetector",
]
