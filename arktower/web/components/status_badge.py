"""YoRHa-styled status badge and priority indicator components."""

from __future__ import annotations

from nicegui import ui

from arktower.web.theme import YORHA_PRIORITY, YORHA_STATUS, get_priority_colors, get_status_colors

STATUS_COLORS = YORHA_STATUS

PRIORITY_COLORS = YORHA_PRIORITY


def status_badge(status: str) -> ui.badge:
    """Render a military-classification-style status badge."""
    colors = get_status_colors().get(
        status, {"text": "#8A8172", "border": "#555"}
    )
    label = f"[{status.upper()}]"
    return (
        ui.badge(label)
        .style(
            f"background: transparent; color: {colors['text']};"
            f" border: 1px solid {colors['border']}; border-radius: 0;"
            " font-family: 'Rajdhani', monospace; letter-spacing: 1px;"
            " text-transform: uppercase; font-size: 0.7rem; padding: 2px 8px;"
        )
    )


def priority_indicator(priority: str) -> ui.badge:
    """Render a YoRHa-styled priority badge."""
    color = get_priority_colors().get(priority, "#8A8172")
    label = f"[{priority.upper()}]"
    return (
        ui.badge(label)
        .style(
            f"background: transparent; color: {color};"
            f" border: 1px solid {color}; border-radius: 0;"
            " font-family: 'Rajdhani', monospace; letter-spacing: 1px;"
            " text-transform: uppercase; font-size: 0.7rem; padding: 2px 8px;"
        )
    )
