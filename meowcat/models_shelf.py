# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""Built-in LLM provider catalog — 12 entries for ModelShelf.

Each :class:`ProviderEntry` carries display_name, auth_type (api-key / token / none),
and default_base_url.  The catalog is consumed by :class:`ModelShelf` which supports
``discover()`` (T-13) for probing available models, and will later support
``register()`` / ``FallbackChain`` (T-14).

.. versionadded:: 1.3.6
"""

from __future__ import annotations

import json
import logging
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Literal, TypeVar

import anyio

from meowcat.models import ModelConfig

logger = logging.getLogger("meowcat.models_shelf")

_T = TypeVar("_T")

AuthType = Literal["api-key", "token", "none"]


@dataclass
class ProviderEntry:
    """A single provider entry in the built-in catalog.

    Usage::

        entry = ProviderEntry(
            display_name="OpenAI",
            auth_type="api-key",
            default_base_url="https://api.openai.com/v1",
        )
    """
    display_name: str
    """Human-readable provider name, e.g. ``"OpenAI"``, ``"DeepSeek"``."""

    auth_type: AuthType
    """Authentication method: ``"api-key"`` / ``"token"`` / ``"none"``."""

    default_base_url: str
    """Default OpenAI-compatible API base URL.  Empty for ``custom-openai``
    (user must supply their own)."""


BUILTIN_PROVIDERS: dict[str, ProviderEntry] = {
    # ── International ──────────────────────────────────────────────
    "openai": ProviderEntry(
        display_name="OpenAI",
        auth_type="api-key",
        default_base_url="https://api.openai.com/v1",
    ),
    "deepseek": ProviderEntry(
        display_name="DeepSeek",
        auth_type="api-key",
        default_base_url="https://api.deepseek.com/v1",
    ),
    "anthropic": ProviderEntry(
        display_name="Anthropic",
        auth_type="api-key",
        default_base_url="https://api.anthropic.com/v1",
    ),
    # ── MiniMax (two auth modes) ───────────────────────────────────
    "minimax-api": ProviderEntry(
        display_name="MiniMax (API Key)",
        auth_type="api-key",
        default_base_url="https://api.minimax.chat/v1",
    ),
    "minimax-token": ProviderEntry(
        display_name="MiniMax (Token)",
        auth_type="token",
        default_base_url="https://api.minimax.chat/v1",
    ),
    # ── Aliyun Bailian (two auth modes) ────────────────────────────
    "aliyun-api": ProviderEntry(
        display_name="Aliyun Bailian (API Key)",
        auth_type="api-key",
        default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    ),
    "aliyun-token": ProviderEntry(
        display_name="Aliyun Bailian (Token)",
        auth_type="token",
        default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    ),
    # ── Chinese domestic ───────────────────────────────────────────
    "moonshot": ProviderEntry(
        display_name="Moonshot",
        auth_type="api-key",
        default_base_url="https://api.moonshot.cn/v1",
    ),
    "zhipu": ProviderEntry(
        display_name="ZhipuAI",
        auth_type="api-key",
        default_base_url="https://open.bigmodel.cn/api/paas/v4",
    ),
    "baidu": ProviderEntry(
        display_name="Baidu Qianfan",
        auth_type="api-key",
        default_base_url="https://qianfan.baidubce.com/v2",
    ),
    # ── Local / Custom ─────────────────────────────────────────────
    "ollama": ProviderEntry(
        display_name="Ollama (Local)",
        auth_type="none",
        default_base_url="http://localhost:11434/v1",
    ),
    "custom-openai": ProviderEntry(
        display_name="Custom (OpenAI-compatible)",
        auth_type="api-key",
        default_base_url="",
    ),
}
"""Built-in provider catalog — 12 entries covering international, Chinese domestic,
local, and custom providers.  Each entry is a :class:`ProviderEntry` keyed by a
short machine-readable identifier (e.g. ``"openai"``, ``"deepseek"``).

* ``ollama``: ``auth_type="none"`` — no API key needed, connects to local instance.
* ``custom-openai``: ``default_base_url=""`` — user must supply a URL and API key.
"""


class ModelShelf:
    """LLM model shelf that wraps the built-in provider catalog.

    Provides lookup over :data:`BUILTIN_PROVIDERS`.  T-13 will add ``discover()``
    (probe a provider for available models).  T-14 will add ``register()`` for
    stocking named configs and ``FallbackChain`` for cascading failover.

    Usage::

        shelf = ModelShelf()
        entry = shelf.get_entry("deepseek")
        # → ProviderEntry(display_name="DeepSeek", auth_type="api-key", ...)

        # List all keys
        keys = shelf.list_entries()
        # → ["openai", "deepseek", "anthropic", ...]

        # Get default base URL
        url = shelf.get_default_url("openai")
        # → "https://api.openai.com/v1"
    """

    def __init__(self, providers: dict[str, ProviderEntry] | None = None) -> None:
        self._providers: dict[str, ProviderEntry] = dict(
            providers if providers is not None else BUILTIN_PROVIDERS
        )
        self._models: dict[str, ModelConfig] = {}

    # -- Catalog queries -------------------------------------------------

    @property
    def providers(self) -> dict[str, ProviderEntry]:
        """Read-only copy of the provider catalog."""
        return dict(self._providers)

    def get_entry(self, key: str) -> ProviderEntry | None:
        """Look up a single provider entry by key (e.g. ``"openai"``).

        Returns ``None`` when the key is not found.
        """
        return self._providers.get(key)

    def list_entries(self) -> list[str]:
        """Return all provider keys in insertion order."""
        return list(self._providers.keys())

    def get_default_url(self, key: str) -> str:
        """Return the default base URL for a provider.

        Raises:
            KeyError: Provider key not found in catalog.
        """
        entry = self._providers.get(key)
        if entry is None:
            raise KeyError(
                f"Provider '{key}' not found in catalog. "
                f"Available: {list(self._providers.keys())}"
            )
        return entry.default_base_url

    # -- Discovery (T-13) ------------------------------------------------

    @staticmethod
    def _http_get_json(url: str, headers: dict[str, str], timeout: float) -> dict:
        """Blocking HTTP GET → parsed JSON dict (runs in thread via anyio)."""
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)  # type: ignore[no-any-return]
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"HTTP {exc.code} from {url}: {exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Cannot reach {url}: {exc.reason}"
            ) from exc

    async def discover(
        self,
        entry: str | ProviderEntry,
        api_key: str = "",
        base_url: str | None = None,
        *,
        timeout: float = 15.0,
    ) -> list[str]:
        """Probe a provider for available model names.

        For OpenAI-compatible providers (``auth_type="api-key"`` or ``"token"``),
        calls ``GET {base_url}/models`` with ``Authorization: Bearer {api_key}``.
        For ollama (``auth_type="none"``), calls ``GET {base_url}/api/tags``
        without authentication.

        Args:
            entry: Provider key (e.g. ``"openai"``) or a :class:`ProviderEntry`.
            api_key: API key or token.  Not needed for ollama.
            base_url: Override the default base URL.  Required when the
                provider entry has an empty ``default_base_url`` (e.g.
                ``"custom-openai"``).
            timeout: HTTP request timeout in seconds.

        Returns:
            List of model name strings, e.g. ``["gpt-4o", "gpt-4o-mini"]``.

        Raises:
            ValueError: Entry not found, or ``base_url`` is empty and cannot
                be determined.
            RuntimeError: HTTP error or network failure.
        """
        # Resolve entry
        if isinstance(entry, str):
            resolved = self._providers.get(entry)
            if resolved is None:
                raise ValueError(
                    f"Provider '{entry}' not found in catalog. "
                    f"Available: {list(self._providers.keys())}"
                )
        else:
            resolved = entry

        # Determine base URL
        if base_url is None:
            base_url = resolved.default_base_url
        if not base_url:
            raise ValueError(
                f"Provider '{resolved.display_name}' has no default_base_url. "
                f"Supply base_url=... explicitly."
            )
        base_url = base_url.rstrip("/")

        # Build headers
        headers: dict[str, str] = {"Accept": "application/json"}
        if resolved.auth_type != "none" and api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # Ollama special case
        if resolved.default_base_url.startswith("http://localhost") or \
                resolved.auth_type == "none":
            url = f"{base_url}/api/tags"
            data = await anyio.to_thread.run_sync(
                self._http_get_json, url, headers, timeout,
            )
            # Ollama format: {"models": [{"name": "llama3.2:latest", ...}, ...]}
            models: list[dict] = data.get("models", [])
            return [m["name"] for m in models if isinstance(m, dict) and "name" in m]

        # OpenAI-compatible /models endpoint
        url = f"{base_url}/models"
        data = await anyio.to_thread.run_sync(
            self._http_get_json, url, headers, timeout,
        )
        # OpenAI format: {"data": [{"id": "gpt-4o", ...}, ...]}
        items: list[dict] = data.get("data", [])
        return [m["id"] for m in items if isinstance(m, dict) and "id" in m]

    # -- Model registry (T-14) -------------------------------------------

    def register(self, name: str, config: ModelConfig) -> None:
        """Stock a named :class:`ModelConfig` on the shelf (overwrites if exists).

        Usage::

            shelf.register("fast", ModelConfig(model="gpt-4o-mini"))
            shelf.register("smart", ModelConfig(model="gpt-4o"))
        """
        self._models[name] = config

    def unregister(self, name: str) -> bool:
        """Remove a model from the shelf. Returns True if removed."""
        return self._models.pop(name, None) is not None

    def list_models(self) -> list[str]:
        """Return all registered model names in insertion order."""
        return list(self._models.keys())

    def get_model(self, name: str) -> ModelConfig:
        """Get a registered model config by name.

        Raises:
            KeyError: Model name not found.
        """
        if name not in self._models:
            raise KeyError(
                f"Model '{name}' not found on shelf. "
                f"Available: {list(self._models.keys())}"
            )
        return self._models[name]

    @property
    def models(self) -> dict[str, ModelConfig]:
        """Read-only copy of the registered model configs."""
        return dict(self._models)


class FallbackChain:
    """Cascading failover executor — tries models in order until one succeeds.

    Application layer configures the fallback order by passing an ordered list
    of model names and a :class:`ModelShelf` reference.  When ``execute()`` is
    called, it tries each model in sequence; on failure the error is logged
    and the next model is attempted.  If all models fail, a :exc:`RuntimeError`
    is raised with aggregated error details.

    Usage::

        shelf = ModelShelf()
        shelf.register("fast", ModelConfig(model="gpt-4o-mini"))
        shelf.register("smart", ModelConfig(model="gpt-4o"))
        shelf.register("fallback", ModelConfig(model="deepseek-v3",
                                                 provider="deepseek"))

        chain = FallbackChain(["fast", "smart", "fallback"], shelf)

        async def call_llm(config: ModelConfig, prompt: str) -> str:
            # app-layer LLM invocation
            return await some_llm_client.generate(config, prompt)

        result = await chain.execute(call_llm, "Hello!")
    """

    def __init__(
        self,
        model_names: list[str],
        shelf: ModelShelf,
    ) -> None:
        if not model_names:
            raise ValueError("FallbackChain requires at least one model name")
        # Resolve all configs eagerly — fail fast if any name is unknown
        self._configs: list[ModelConfig] = [
            shelf.get_model(name) for name in model_names
        ]

    @property
    def model_names(self) -> list[str]:
        """Ordered list of model names in this chain."""
        return [c.model for c in self._configs]

    async def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute ``func(config, *args, **kwargs)`` against each model in order.

        ``func`` receives a :class:`ModelConfig` as its first positional argument
        followed by ``*args`` and ``**kwargs``.  It may be sync or async —
        :meth:`execute` auto-detects via :func:`inspect.iscoroutinefunction`.

        Args:
            func: Callable ``(ModelConfig, *args, **kwargs) -> T``.
            *args, **kwargs: Forwarded to ``func`` after the config.

        Returns:
            The return value of the first successful ``func`` call.

        Raises:
            RuntimeError: All models in the chain failed.
        """
        import inspect

        errors: list[tuple[str, str]] = []
        is_async = inspect.iscoroutinefunction(func)

        for cfg in self._configs:
            try:
                if is_async:
                    return await func(cfg, *args, **kwargs)
                else:
                    result = func(cfg, *args, **kwargs)
                    # If func is sync but returns an awaitable, await it
                    if inspect.isawaitable(result):
                        return await result
                    return result
            except Exception as exc:
                logger.warning(
                    "FallbackChain: model '%s' failed: %s",
                    cfg.model, exc,
                )
                errors.append((cfg.model, str(exc)))

        raise RuntimeError(
            f"FallbackChain: all {len(self._configs)} models failed. "
            + "; ".join(f"{m}: {e[:80]}" for m, e in errors)
        )


__all__ = ["ProviderEntry", "AuthType",
           "BUILTIN_PROVIDERS", "ModelShelf", "FallbackChain"]
