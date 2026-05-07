# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""
v1.3.6 — ModelShelf + FallbackChain 全覆盖测试
================================================

验证:
    1. TestProviderEntry         — ProviderEntry dataclass 字段
    2. TestBuiltinProviders      — 12 内置供应商目录全覆盖
    3. TestModelShelfCatalog     — get_entry / list_entries / get_default_url / providers
    4. TestModelShelfDiscovery   — discover() 探测 mock (OpenAI / Ollama / 错误路径)
    5. TestModelShelfRegistry    — register / unregister / list_models / get_model / models
    6. TestModelConfigRepr       — api_key 脱敏 + 非脱敏
    7. TestFallbackChain         — 构造函数 / model_names / sync execute / 失败回退 / 全失败
    8. TestFallbackChainAsync    — async execute / sync-returns-awaitable / 混合回退
"""

from __future__ import annotations

import json
import urllib.error
from unittest.mock import patch, MagicMock

import pytest

from meowcat.models import ModelConfig
from meowcat.models_shelf import (
    ProviderEntry,
    BUILTIN_PROVIDERS,
    ModelShelf,
    FallbackChain,
)


# ── 1. ProviderEntry ────────────────────────────────────────────────────

class TestProviderEntry:
    """ProviderEntry dataclass 字段。"""

    def test_default_fields(self) -> None:
        entry = ProviderEntry(
            display_name="Test",
            auth_type="api-key",
            default_base_url="https://api.test.com/v1",
        )
        assert entry.display_name == "Test"
        assert entry.auth_type == "api-key"
        assert entry.default_base_url == "https://api.test.com/v1"

    def test_auth_types(self) -> None:
        for at in ("api-key", "token", "none"):
            entry = ProviderEntry("X", at, "https://x.com")
            assert entry.auth_type == at

    def test_empty_base_url_allowed(self) -> None:
        entry = ProviderEntry("Custom", "api-key", "")
        assert entry.default_base_url == ""


# ── 2. Built-in Providers ──────────────────────────────────────────────

class TestBuiltinProviders:
    """12 内置供应商目录全覆盖。"""

    def test_count(self) -> None:
        assert len(BUILTIN_PROVIDERS) == 12

    def test_all_keys_present(self) -> None:
        expected = {
            "openai", "deepseek", "anthropic",
            "minimax-api", "minimax-token",
            "aliyun-api", "aliyun-token",
            "moonshot", "zhipu", "baidu",
            "ollama", "custom-openai",
        }
        assert set(BUILTIN_PROVIDERS.keys()) == expected

    def test_openai(self) -> None:
        e = BUILTIN_PROVIDERS["openai"]
        assert e.display_name == "OpenAI"
        assert e.auth_type == "api-key"
        assert e.default_base_url == "https://api.openai.com/v1"

    def test_deepseek(self) -> None:
        e = BUILTIN_PROVIDERS["deepseek"]
        assert e.display_name == "DeepSeek"
        assert e.auth_type == "api-key"
        assert e.default_base_url == "https://api.deepseek.com/v1"

    def test_anthropic(self) -> None:
        e = BUILTIN_PROVIDERS["anthropic"]
        assert e.display_name == "Anthropic"
        assert e.auth_type == "api-key"

    def test_minimax_both_modes(self) -> None:
        api_entry = BUILTIN_PROVIDERS["minimax-api"]
        assert api_entry.auth_type == "api-key"
        token_entry = BUILTIN_PROVIDERS["minimax-token"]
        assert token_entry.auth_type == "token"
        assert api_entry.default_base_url == token_entry.default_base_url

    def test_aliyun_both_modes(self) -> None:
        api_entry = BUILTIN_PROVIDERS["aliyun-api"]
        assert api_entry.auth_type == "api-key"
        token_entry = BUILTIN_PROVIDERS["aliyun-token"]
        assert token_entry.auth_type == "token"
        assert api_entry.default_base_url == token_entry.default_base_url

    def test_ollama_local(self) -> None:
        e = BUILTIN_PROVIDERS["ollama"]
        assert e.auth_type == "none"
        assert e.default_base_url == "http://localhost:11434/v1"

    def test_custom_openai(self) -> None:
        e = BUILTIN_PROVIDERS["custom-openai"]
        assert e.auth_type == "api-key"
        assert e.default_base_url == ""

    def test_chinese_domestic(self) -> None:
        for key in ("moonshot", "zhipu", "baidu"):
            e = BUILTIN_PROVIDERS[key]
            assert e.auth_type == "api-key"
            assert e.default_base_url  # non-empty

    def test_all_entries_are_provider_entry(self) -> None:
        for key, entry in BUILTIN_PROVIDERS.items():
            assert isinstance(
                entry, ProviderEntry), f"{key} is not ProviderEntry"

    def test_all_have_display_name(self) -> None:
        for key, entry in BUILTIN_PROVIDERS.items():
            assert entry.display_name, f"{key} has empty display_name"


# ── 3. ModelShelf Catalog ──────────────────────────────────────────────

class TestModelShelfCatalog:
    """ModelShelf 供应商目录查询操作。"""

    def test_get_entry_found(self) -> None:
        shelf = ModelShelf()
        entry = shelf.get_entry("openai")
        assert entry is not None
        assert entry.display_name == "OpenAI"

    def test_get_entry_not_found(self) -> None:
        shelf = ModelShelf()
        assert shelf.get_entry("nonexistent") is None

    def test_list_entries(self) -> None:
        shelf = ModelShelf()
        keys = shelf.list_entries()
        assert len(keys) == 12
        assert keys[0] == "openai"

    def test_list_entries_order(self) -> None:
        shelf = ModelShelf()
        keys = shelf.list_entries()
        assert keys == list(BUILTIN_PROVIDERS.keys())

    def test_get_default_url(self) -> None:
        shelf = ModelShelf()
        assert shelf.get_default_url("openai") == "https://api.openai.com/v1"

    def test_get_default_url_not_found(self) -> None:
        shelf = ModelShelf()
        with pytest.raises(KeyError, match="nonexistent"):
            shelf.get_default_url("nonexistent")

    def test_providers_is_copy(self) -> None:
        shelf = ModelShelf()
        copy1 = shelf.providers
        copy2 = shelf.providers
        assert copy1 == copy2
        assert copy1 is not copy2  # different dict objects
        copy1["fake"] = ProviderEntry("Fake", "none", "")
        assert "fake" not in shelf.providers

    def test_custom_providers_in_init(self) -> None:
        custom = {"test": ProviderEntry(
            "Test", "none", "http://localhost:8080")}
        shelf = ModelShelf(providers=custom)
        assert shelf.list_entries() == ["test"]
        assert shelf.get_entry("openai") is None


# ── 4. ModelShelf Discovery ────────────────────────────────────────────

class TestModelShelfDiscovery:
    """discover() 探测 mock 测试。"""

    @pytest.mark.anyio
    async def test_discover_openai_format(self) -> None:
        """模拟 OpenAI-compatible /models 端点返回。"""
        shelf = ModelShelf()
        mock_data = json.dumps({
            "data": [
                {"id": "gpt-4o", "object": "model"},
                {"id": "gpt-4o-mini", "object": "model"},
            ]
        }).encode()

        with patch.object(shelf, "_http_get_json",
                          return_value=json.loads(mock_data)) as mock_http:
            models = await shelf.discover("openai", api_key="sk-test")
            assert models == ["gpt-4o", "gpt-4o-mini"]
            # Verify URL construction
            call_url = mock_http.call_args[0][0]
            assert call_url == "https://api.openai.com/v1/models"

    @pytest.mark.anyio
    async def test_discover_ollama_format(self) -> None:
        """模拟 Ollama /api/tags 端点返回。"""
        shelf = ModelShelf()
        mock_data = json.dumps({
            "models": [
                {"name": "llama3.2:latest"},
                {"name": "mistral:7b"},
            ]
        }).encode()

        with patch.object(shelf, "_http_get_json",
                          return_value=json.loads(mock_data)) as mock_http:
            models = await shelf.discover("ollama")
            assert models == ["llama3.2:latest", "mistral:7b"]
            call_url = mock_http.call_args[0][0]
            assert call_url.endswith("/api/tags")

    @pytest.mark.anyio
    async def test_discover_by_entry_object(self) -> None:
        """discover 接受 ProviderEntry 对象而非字符串 key。"""
        shelf = ModelShelf()
        entry = ProviderEntry("Custom", "api-key", "https://custom.api/v1")
        mock_data = json.dumps({
            "data": [{"id": "custom-model"}]
        }).encode()

        with patch.object(shelf, "_http_get_json",
                          return_value=json.loads(mock_data)):
            models = await shelf.discover(entry, api_key="sk-xxx")
            assert models == ["custom-model"]

    @pytest.mark.anyio
    async def test_discover_base_url_override(self) -> None:
        """base_url 参数可覆盖默认 URL。"""
        shelf = ModelShelf()
        mock_data = json.dumps({
            "data": [{"id": "proxy-model"}]
        }).encode()

        with patch.object(shelf, "_http_get_json",
                          return_value=json.loads(mock_data)) as mock_http:
            models = await shelf.discover(
                "openai", api_key="sk-test",
                base_url="https://my-proxy.com/v1",
            )
            assert models == ["proxy-model"]
            assert mock_http.call_args[0][0] == "https://my-proxy.com/v1/models"

    @pytest.mark.anyio
    async def test_discover_custom_openai_requires_base_url(self) -> None:
        """custom-openai 无 default_base_url，不传 base_url 应抛错。"""
        shelf = ModelShelf()
        with pytest.raises(ValueError, match="no default_base_url"):
            await shelf.discover("custom-openai", api_key="sk-test")

    @pytest.mark.anyio
    async def test_discover_custom_openai_with_base_url(self) -> None:
        """custom-openai 传 base_url 后可正常探测。"""
        shelf = ModelShelf()
        mock_data = json.dumps({
            "data": [{"id": "my-model"}]
        }).encode()

        with patch.object(shelf, "_http_get_json",
                          return_value=json.loads(mock_data)):
            models = await shelf.discover(
                "custom-openai", api_key="sk-test",
                base_url="https://my.api/v1",
            )
            assert models == ["my-model"]

    @pytest.mark.anyio
    async def test_discover_unknown_provider(self) -> None:
        """不存在的 provider key 抛 ValueError。"""
        shelf = ModelShelf()
        with pytest.raises(ValueError, match="nonexistent"):
            await shelf.discover("nonexistent", api_key="sk-test")

    @pytest.mark.anyio
    async def test_discover_http_error(self) -> None:
        """HTTP 错误时应抛 RuntimeError。"""
        shelf = ModelShelf()
        with patch.object(shelf, "_http_get_json",
                          side_effect=RuntimeError("HTTP 401 from ...: Unauthorized")):
            with pytest.raises(RuntimeError, match="HTTP 401"):
                await shelf.discover("openai", api_key="bad-key")

    @pytest.mark.anyio
    async def test_discover_empty_models_list(self) -> None:
        """空模型列表返回 []。"""
        shelf = ModelShelf()
        mock_data = json.dumps({"data": []}).encode()

        with patch.object(shelf, "_http_get_json",
                          return_value=json.loads(mock_data)):
            models = await shelf.discover("openai", api_key="sk-test")
            assert models == []

    @pytest.mark.anyio
    async def test_discover_missing_data_key(self) -> None:
        """响应缺少 'data' 键时返回 []。"""
        shelf = ModelShelf()
        with patch.object(shelf, "_http_get_json", return_value={"other": "value"}):
            models = await shelf.discover("openai", api_key="sk-test")
            assert models == []


# ── 5. ModelShelf Registry ─────────────────────────────────────────────

class TestModelShelfRegistry:
    """ModelShelf 模型注册表操作。"""

    def test_register_and_get(self) -> None:
        shelf = ModelShelf()
        cfg = ModelConfig(model="gpt-4o-mini")
        shelf.register("fast", cfg)
        assert shelf.get_model("fast") is cfg

    def test_register_overwrite(self) -> None:
        shelf = ModelShelf()
        cfg1 = ModelConfig(model="gpt-4o-mini")
        cfg2 = ModelConfig(model="gpt-4o")
        shelf.register("default", cfg1)
        shelf.register("default", cfg2)
        assert shelf.get_model("default") is cfg2

    def test_get_model_not_found(self) -> None:
        shelf = ModelShelf()
        with pytest.raises(KeyError, match="nope"):
            shelf.get_model("nope")

    def test_unregister_existing(self) -> None:
        shelf = ModelShelf()
        shelf.register("fast", ModelConfig(model="gpt-4o-mini"))
        assert shelf.unregister("fast") is True
        assert shelf.list_models() == []

    def test_unregister_nonexistent(self) -> None:
        shelf = ModelShelf()
        assert shelf.unregister("nope") is False

    def test_list_models_empty(self) -> None:
        shelf = ModelShelf()
        assert shelf.list_models() == []

    def test_list_models_order(self) -> None:
        shelf = ModelShelf()
        shelf.register("c", ModelConfig(model="c"))
        shelf.register("a", ModelConfig(model="a"))
        shelf.register("b", ModelConfig(model="b"))
        assert shelf.list_models() == ["c", "a", "b"]

    def test_models_is_copy(self) -> None:
        shelf = ModelShelf()
        shelf.register("fast", ModelConfig(model="gpt-4o-mini"))
        copy1 = shelf.models
        copy2 = shelf.models
        assert copy1 == copy2
        assert copy1 is not copy2
        copy1["new"] = ModelConfig(model="fake")
        assert "new" not in shelf.models


# ── 6. ModelConfig repr (key 脱敏) ─────────────────────────────────────

class TestModelConfigRepr:
    """ModelConfig __repr__ 中的 api_key 脱敏。"""

    def test_api_key_masked_in_repr(self) -> None:
        cfg = ModelConfig(model="gpt-4o", api_key="sk-1234567890abcdef")
        r = repr(cfg)
        assert "sk-***" in r
        assert "sk-1234567890abcdef" not in r

    def test_empty_api_key_no_mask(self) -> None:
        cfg = ModelConfig(model="gpt-4o-mini", api_key="")
        r = repr(cfg)
        assert "sk-***" not in r
        assert "api_key=''" in r

    def test_repr_contains_model_name(self) -> None:
        cfg = ModelConfig(model="deepseek-v3", provider="deepseek",
                          api_key="sk-secret")
        r = repr(cfg)
        assert "deepseek-v3" in r
        assert "deepseek" in r


# ── 7. FallbackChain Sync ──────────────────────────────────────────────

class TestFallbackChain:
    """FallbackChain 同步执行 + 失败回退。"""

    def _make_shelf(self, *names: str) -> ModelShelf:
        shelf = ModelShelf()
        for n in names:
            shelf.register(n, ModelConfig(model=n))
        return shelf

    @pytest.mark.anyio
    async def test_first_model_succeeds(self) -> None:
        shelf = self._make_shelf("fast", "smart")
        chain = FallbackChain(["fast", "smart"], shelf)

        calls: list[str] = []

        def invoke(cfg: ModelConfig) -> str:
            calls.append(cfg.model)
            return f"result-from-{cfg.model}"

        result = await chain.execute(invoke)
        assert result == "result-from-fast"
        assert calls == ["fast"]  # only first called

    @pytest.mark.anyio
    async def test_fallback_on_failure(self) -> None:
        shelf = self._make_shelf("fast", "smart", "fallback")
        chain = FallbackChain(["fast", "smart", "fallback"], shelf)

        calls: list[str] = []

        def invoke(cfg: ModelConfig) -> str:
            calls.append(cfg.model)
            if cfg.model == "fast":
                raise RuntimeError("fast down")
            if cfg.model == "smart":
                raise RuntimeError("smart down")
            return f"result-from-{cfg.model}"

        result = await chain.execute(invoke)
        assert result == "result-from-fallback"
        assert calls == ["fast", "smart", "fallback"]

    @pytest.mark.anyio
    async def test_all_fail_raises(self) -> None:
        shelf = self._make_shelf("a", "b")
        chain = FallbackChain(["a", "b"], shelf)

        def invoke(cfg: ModelConfig) -> str:
            raise RuntimeError(f"{cfg.model} error")

        with pytest.raises(RuntimeError, match="all 2 models failed"):
            await chain.execute(invoke)

    @pytest.mark.anyio
    async def test_empty_chain_raises(self) -> None:
        shelf = ModelShelf()
        with pytest.raises(ValueError, match="at least one"):
            FallbackChain([], shelf)

    def test_model_names_property(self) -> None:
        shelf = self._make_shelf("fast", "smart")
        chain = FallbackChain(["fast", "smart"], shelf)
        assert chain.model_names == ["fast", "smart"]

    @pytest.mark.anyio
    async def test_unknown_model_raises_on_init(self) -> None:
        shelf = self._make_shelf("fast")
        with pytest.raises(KeyError, match="unknown"):
            FallbackChain(["fast", "unknown"], shelf)


# ── 8. FallbackChain Async ─────────────────────────────────────────────

class TestFallbackChainAsync:
    """FallbackChain async 执行 + sync-returns-awaitable 路径。"""

    def _make_shelf(self, *names: str) -> ModelShelf:
        shelf = ModelShelf()
        for n in names:
            shelf.register(n, ModelConfig(model=n))
        return shelf

    @pytest.mark.anyio
    async def test_async_func(self) -> None:
        shelf = self._make_shelf("fast", "smart")
        chain = FallbackChain(["fast", "smart"], shelf)

        async def invoke(cfg: ModelConfig) -> str:
            return f"async-{cfg.model}"

        result = await chain.execute(invoke)
        assert result == "async-fast"

    @pytest.mark.anyio
    async def test_async_fallback(self) -> None:
        shelf = self._make_shelf("fast", "smart")
        chain = FallbackChain(["fast", "smart"], shelf)

        async def invoke(cfg: ModelConfig) -> str:
            if cfg.model == "fast":
                raise RuntimeError("down")
            return f"async-{cfg.model}"

        result = await chain.execute(invoke)
        assert result == "async-smart"

    @pytest.mark.anyio
    async def test_sync_returns_awaitable(self) -> None:
        """sync 函数返回 awaitable 时自动 await。"""
        shelf = self._make_shelf("fast")
        chain = FallbackChain(["fast"], shelf)

        async def _inner(cfg: ModelConfig) -> str:
            return f"awaited-{cfg.model}"

        def invoke(cfg: ModelConfig):
            return _inner(cfg)  # returns coroutine

        result = await chain.execute(invoke)
        assert result == "awaited-fast"

    @pytest.mark.anyio
    async def test_async_all_fail(self) -> None:
        shelf = self._make_shelf("a", "b", "c")
        chain = FallbackChain(["a", "b", "c"], shelf)

        async def invoke(cfg: ModelConfig) -> str:
            raise RuntimeError(f"{cfg.model} failed")

        with pytest.raises(RuntimeError, match="all 3 models failed"):
            await chain.execute(invoke)
