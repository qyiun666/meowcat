# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat plus/gateway — concrete protocol adapter implementations.

These are optional batteries providing real I/O adapters (HTTP, WebSocket,
Webhook, CLI, IPC). Keep ``meowcat/gateway/`` for pure abstractions
(Gateway, IoAdapterProtocol, SignalContext).

Usage::

    from meowcat.plus.gateway import HttpAdapter, CliAdapter
"""

from __future__ import annotations

from meowcat.plus.gateway.http_adapter import HttpAdapter
from meowcat.plus.gateway.ws_adapter import WsAdapter
from meowcat.plus.gateway.webhook_adapter import WebhookAdapter
from meowcat.plus.gateway.cli_adapter import CliAdapter
from meowcat.plus.gateway.ipc_adapter import IpcAdapter

__all__ = [
    "HttpAdapter",
    "WsAdapter",
    "WebhookAdapter",
    "CliAdapter",
    "IpcAdapter",
]

