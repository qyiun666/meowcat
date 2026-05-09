# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat I18n — multi-language engine with builtin en/zh locales (v1.1.9).

Pluggable design: register new languages via ``plug("language", code, data)``.
Default: ``I18n(lang="en")``. Switch at runtime via ``i18n.lang = "zh"``.

Builtin locales are embedded as package data in ``meowcat/cli/locales/``.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

from meowcat.pluggable import Pluggable


class I18n(Pluggable):
    """Multi-language translation engine.

    Extension slot ``"language"``: register a new language at runtime.

    Usage::

        i18n = I18n(lang="en")
        i18n.t("unknown_command", cmd="/foo")  # → "Unknown command: /foo"

        i18n.lang = "zh"
        i18n.t("unknown_command", cmd="/foo")  # → "未知命令: /foo"

        # Register custom language
        i18n.plug("language", "ja", {"unknown_command": "不明なコマンド: {cmd}"})
        i18n.lang = "ja"
    """

    HOOKS: dict[str, dict[str, str]] = {
        "language": {"in": "lang_code: str, data: dict", "out": "None"},
    }

    _LOCALES_DIR = pathlib.Path(__file__).resolve().parent / "locales"
    _BUILTIN = ("en", "zh")

    def __init__(self, lang: str = "en") -> None:
        super().__init__()
        self._locales: dict[str, dict[str, str]] = {}
        self._lang = lang
        self._load_builtin()

    # -- Builtin loader ------------------------------------------------

    def _load_builtin(self) -> None:
        """Load builtin locale files from the package."""
        for code in self._BUILTIN:
            path = self._LOCALES_DIR / f"{code}.json"
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self._locales[code] = data
            except (FileNotFoundError, json.JSONDecodeError):
                self._locales[code] = {}

    # -- Core API ------------------------------------------------------

    @property
    def lang(self) -> str:
        """Current active language code."""
        return self._lang

    @lang.setter
    def lang(self, value: str) -> None:
        if value not in self._locales:
            # Try running plugins to see if one can supply the language
            for _hook, r in self._run_plugs_sync("language", value, None):
                if isinstance(r, dict):
                    self._locales[value] = r
                    break
        if value not in self._locales:
            raise ValueError(
                f"Unsupported language '{value}'. Available: {list(self._locales.keys())}"
            )
        self._lang = value

    def t(self, key: str, **kwargs: Any) -> str:
        """Translate a key with optional placeholder substitution.

        Args:
            key: Translation key (dot-separated, e.g. ``"unknown_command"``).
            **kwargs: Placeholder values for formatting.

        Returns:
            Translated string with placeholders filled, or the key itself
            if translation is missing.
        """
        locale = self._locales.get(self._lang, {})
        template = locale.get(key)
        if template is None:
            return key
        try:
            return template.format(**kwargs)
        except (KeyError, ValueError):
            return template

    # -- Language management -------------------------------------------

    def add_language(self, code: str, data: dict[str, str]) -> None:
        """Register a new language or override an existing one.

        Args:
            code: Language code (e.g. ``"ja"``, ``"fr"``).
            data: Translation dict ``{key: template, ...}``.
        """
        existing = self._locales.get(code, {})
        self._locales[code] = {**existing, **data}

    @property
    def supported_languages(self) -> list[str]:
        """List all registered language codes."""
        return sorted(self._locales.keys())

    # -- Pluggable hook — "language" slot -------------------------------

    def plug(self, slot: str, code: str, data: dict[str, str] | None = None) -> None:  # type: ignore[override]
        """Extended plug for I18n — ``"language"`` slot registers a new language.

        Usage::

            i18n.plug("language", "ja", {"hello": "こんにちは"})
            i18n.plug("language", "fr", {"hello": "Bonjour"})

        Args:
            slot: Hook name (``"language"`` is the only custom slot).
            code: Language code.
            data: Translation dict. When None, falls back to standard
                  ``mount_plug`` behavior for general hooks.
        """
        if slot == "language" and data is not None:
            self.add_language(code, data)
        else:
            super().plug(slot, code)  # type: ignore[arg-type]


__all__ = ["I18n"]
