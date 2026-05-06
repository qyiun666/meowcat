# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat utility modules — shared helpers with zero framework dependency.

``meowcat/utils/`` has zero meowagent dependency.
"""
# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT


from __future__ import annotations

from meowcat.utils.http import close_shared_client, get_shared_client

__all__ = [
    "get_shared_client",
    "close_shared_client",
]

