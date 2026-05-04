"""meowcat Textual TUI — bare-bones App skeleton for agent TUIs (v1.1.13).

Layout::

    ┌──────────────────────────────────┐
    │  Chat / Log Area (VerticalScroll) │
    ├──────────────────────────────────┤
    │  Input Area (TextArea)            │
    ├──────────────────────────────────┤
    │  Footer                          │
    └──────────────────────────────────┘

Extend :class:`MeowTui` and override :meth:`compose` to customise.
"""
# (c) 2025-2026 Axonant. MIT License.

from __future__ import annotations

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Footer, TextArea


class MeowTui(App[None]):
    """Textual TUI skeleton — layout + bindings, no opinionated widgets.

    Subclass and override ``compose()`` to add your own widgets.
    """

    CSS: ClassVar[str] = """
    Screen {
        background: #0d1117;
        color: #e0e0f0;
    }
    #chat-scroll {
        height: 1fr;
        border-bottom: solid #30363d;
    }
    #tui-input {
        height: 6;
        background: #161b22;
        border-bottom: solid #30363d;
        padding: 0 1;
    }
    #tui-input:focus {
        border-bottom: solid #58a6ff;
    }
    """

    BINDINGS = [
        ("ctrl+d", "quit", "Quit"),
        ("ctrl+l", "clear_chat", "Clear"),
    ]

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="chat-scroll")
        yield TextArea(id="tui-input")
        yield Footer()

    # -- Helpers ---------------------------------------------------------------

    def add_line(self, text: str) -> None:
        """Append a line of text to the chat area."""
        from textual.widgets import Static

        scroll = self.query_one("#chat-scroll", VerticalScroll)
        scroll.mount(Static(text))
        scroll.scroll_end(animate=False)

    # -- Actions ---------------------------------------------------------------

    async def action_quit(self) -> None:
        self.exit()

    def action_clear_chat(self) -> None:
        scroll = self.query_one("#chat-scroll", VerticalScroll)
        for child in list(scroll.children):
            child.remove()
