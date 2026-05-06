# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""Colony configuration — nameplate snapshot and owner profile.

ColonyConfig is a serializable snapshot of the colony's nameplate.
ColonyOwner carries the human owner's identity and preferences.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

class ColonyConfig:
    """Colony configuration — nameplate snapshot for serialization/restore."""
    name: str | None = None
    description: str = ""
    max_cats: int | None = None
# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT



@dataclass
class ColonyOwner:
    """Colony owner profile — name, contact, language preference.

    Usage::

        ColonyOwner(name="张三", email="zhang@corp.com", language="zh")
        ColonyOwner(name="Li Si", extra={"slack_id": "U123", "role": "admin"})
    """
    name: str = ""
    email: str = ""
    language: str = "en"
    extra: dict[str, Any] = field(default_factory=dict)

