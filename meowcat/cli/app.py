# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat Textual TUI — slot-based composable App skeleton for agent TUIs (v1.2.36).

Default layout (single-column)::

    ┌──────────────────────────────────┐
    │  Header                          │
    ├──────────────────────────────────┤
    │  Chat / Log Area (VerticalScroll) │
    ├──────────────────────────────────┤
    │  Input Area (TextArea)            │
    ├──────────────────────────────────┤
    │  Status Bar (Label)              │
    ├──────────────────────────────────┤
    │  Footer                          │
    └──────────────────────────────────┘

Sidebar layout (``show_sidebar=True``)::

    ┌──────────┬───────────────────────┐
    │  Header                          │
    ├──────────┼───────────────────────┤
    │  Sidebar │  Chat / Log Area      │
    │          ├───────────────────────┤
    │          │  Input Area           │
    ├──────────┴───────────────────────┤
    │  Status Bar                      │
    ├──────────────────────────────────┤
    │  Footer                          │
    └──────────────────────────────────┘

Subclass :class:`MeowTui`, set ``show_sidebar=True``, then call
:meth:`mount_slot` to populate the sidebar or other named slots.
"""

from __future__ import annotations

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, Label, LoadingIndicator, TextArea


class MeowTui(App[None]):
    """Textual TUI skeleton — slot-based layout + bindings.

    Subclass and set ``show_sidebar=True`` to enable dual-column layout.
    Use :meth:`mount_slot` to populate named slots (sidebar, main, etc.).
    """
# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT


    CSS: ClassVar[str] = """
    Screen {
        background: #0d1117;
        color: #e0e0f0;
    }
    #sidebar {
        width: 30;
        border-right: solid #30363d;
        background: #161b22;
        padding: 0 1;
    }
# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

    #main {
        width: 1fr;
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
    #status-bar {
        height: 1;
        background: #161b22;
        padding: 0 1;
    }
    """

    BINDINGS = [
        ("ctrl+d", "quit", "Quit"),
        ("ctrl+l", "clear_chat", "Clear"),
    ]

    show_sidebar: bool = False  #: Set True to enable dual-column layout.

    def compose(self) -> ComposeResult:
        yield Header()
        if self.show_sidebar:
            with Horizontal():
                yield VerticalScroll(id="sidebar")
                with Vertical(id="main"):
                    yield VerticalScroll(id="chat-scroll")
                    yield TextArea(id="tui-input")
        else:
            yield VerticalScroll(id="chat-scroll")
            yield TextArea(id="tui-input")
        yield Label("", id="status-bar")
        yield Footer()

    # -- Slot helpers ----------------------------------------------------------

    def mount_slot(self, slot_id: str, widget) -> None:
        """Mount a widget into a named slot container.

        Typical usage::

            self.mount_slot("sidebar", MyProfilePanel())
        """
        container = self.query_one(f"#{slot_id}")
        container.mount(widget)

    def set_status(self, text: str) -> None:
        """Update the status bar text."""
        self.query_one("#status-bar", Label).update(text)

    def add_line(self, text: str) -> None:
        """Append a line of text to the chat area."""
        from textual.widgets import Static

        scroll = self.query_one("#chat-scroll", VerticalScroll)
        scroll.mount(Static(text))
        scroll.scroll_end(animate=False)

    def show_loading(self, text: str = "Thinking...") -> None:
        """Show a loading indicator in the chat area."""
        indicator = LoadingIndicator(id="loading")
        self.mount_slot("chat-scroll", indicator)

    def hide_loading(self) -> None:
        """Remove the loading indicator if present."""
        try:
            self.query_one("#loading", LoadingIndicator).remove()
        except Exception:
            pass

    # -- Actions ---------------------------------------------------------------

    async def action_quit(self) -> None:
        self.exit()

    def action_clear_chat(self) -> None:
        scroll = self.query_one("#chat-scroll", VerticalScroll)
        for child in list(scroll.children):
            if child.id != "loading":
                child.remove()

