# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat CLI theme engine — framework-layer colour/style definitions (v1.1.29).

Provides :class:`Theme` — a zero-brand, neutral colour palette for terminal
and TUI applications. Deliberately avoids brand-specific colours so every
downstream app can apply its own identity on top.

Usage::

    from meowcat.cli.theme import Theme
    print(f"{Theme.GREEN}success{Theme.RESET}")
"""

from __future__ import annotations


class Theme:
    """Framework-layer neutral terminal theme.

    No brand colours. No opinionated palette. Just readable ANSI codes
    suitable as a base for any downstream app's custom theme.
    """

    # -- Reset ----------------------------------------------------------
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    # -- Foreground (neutral, high-contrast) ----------------------------
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # -- Bright foreground ----------------------------------------------
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT


    # -- Background -----------------------------------------------------
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"
# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT


    # -- Semantic aliases (framework-level, no brand mapping) ------------
    SUCCESS = GREEN
    WARNING = YELLOW
    ERROR = RED
    INFO = CYAN
    DEBUG = DIM
    HIGHLIGHT = BOLD
    MUTED = DIM

    # -- Helpers ---------------------------------------------------------

# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

    @staticmethod
    def styled(text: str, *codes: str) -> str:
        """Wrap text in ANSI codes with auto-reset.

        Usage::

            Theme.styled("OK", Theme.GREEN, Theme.BOLD)  # → bold green "OK"
        """
        prefix = "".join(codes)
        return f"{prefix}{text}{Theme.RESET}"

    @classmethod
    def success(cls, text: str) -> str:
        """Green success text."""
        return cls.styled(text, cls.SUCCESS)

    @classmethod
    def warning(cls, text: str) -> str:
        """Yellow warning text."""
        return cls.styled(text, cls.WARNING)

    @classmethod
    def error(cls, text: str) -> str:
        """Red error text."""
        return cls.styled(text, cls.ERROR)

    @classmethod
    def info(cls, text: str) -> str:
        """Cyan info text."""
        return cls.styled(text, cls.INFO)

    @classmethod
    def header(cls, text: str) -> str:
        """Bold highlighted header."""
        return cls.styled(text, cls.HIGHLIGHT)

    @classmethod
    def muted(cls, text: str) -> str:
        """Dim/muted secondary text."""
        return cls.styled(text, cls.MUTED)

    @classmethod
    def to_textual_theme(cls, dark: bool = True) -> dict[str, str]:
        """生成 Textual 兼容主题字典, 供 MeowTui 使用."""
        if dark:
            return {
                "primary": "#58a6ff",
                "secondary": "#30363d",
                "background": "#0d1117",
                "surface": "#161b22",
                "text": "#e0e0f0",
                "text-muted": "#8b949e",
                "error": "#f85149",
                "success": "#3fb950",
                "warning": "#d29922",
                "accent": "#a371f7",
                "border": "#30363d",
            }
        return {
            "primary": "#0969da",
            "secondary": "#d0d7de",
            "background": "#ffffff",
            "surface": "#f6f8fa",
            "text": "#1f2328",
            "text-muted": "#656d76",
            "error": "#cf222e",
            "success": "#1a7f37",
            "warning": "#9a6700",
            "accent": "#8250df",
            "border": "#d0d7de",
        }


__all__ = ["Theme"]

