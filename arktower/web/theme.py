"""YoRHa-inspired design tokens and global CSS for the ArkTower dashboard.

Supports two themes:
  - **dark** — The Tower (original NieR black/gold)
  - **light** — The Resistance Camp (warm beige daytime variant)
"""

from __future__ import annotations

from nicegui import ui

# ---------------------------------------------------------------------------
# Dark theme — The Tower
# ---------------------------------------------------------------------------
YORHA_COLORS_DARK: dict[str, str] = {
    "bg_primary": "#0D0D0D",
    "bg_surface": "#1A1A1A",
    "bg_elevated": "#242424",
    "text_primary": "#DAD4BB",
    "text_muted": "#A89F8A",
    "text_dim": "#8A8172",
    "accent": "#C7372F",
    "accent_dark": "#8B2520",
    "border": "#333333",
    "border_accent": "#C7372F",
}

YORHA_STATUS_DARK: dict[str, dict[str, str]] = {
    "submitted": {"text": "#DAD4BB", "border": "#555"},
    "queued": {"text": "#7FDBCA", "border": "#4A9E8E"},
    "in_progress": {"text": "#DAD4BB", "border": "#C7372F"},
    "review": {"text": "#B8A9C9", "border": "#7E6B9B"},
    "input_required": {"text": "#D4A574", "border": "#B8834A"},
    "blocked": {"text": "#C7372F", "border": "#8B2520"},
    "completed": {"text": "#8BAA7F", "border": "#5C7A52"},
    "failed": {"text": "#C7372F", "border": "#8B2520"},
    "canceled": {"text": "#8A8172", "border": "#555"},
    "timed_out": {"text": "#C7372F", "border": "#8B2520"},
}

YORHA_PRIORITY_DARK: dict[str, str] = {
    "critical": "#C7372F",
    "high": "#D4A574",
    "medium": "#DAD4BB",
    "low": "#8A8172",
}

# ---------------------------------------------------------------------------
# Light theme — The Resistance Camp
# ---------------------------------------------------------------------------
YORHA_COLORS_LIGHT: dict[str, str] = {
    "bg_primary": "#F5F0E8",
    "bg_surface": "#FFFDF8",
    "bg_elevated": "#EDE8DF",
    "text_primary": "#2A2520",
    "text_muted": "#6B6560",
    "text_dim": "#9A9590",
    "accent": "#C7372F",
    "accent_dark": "#A02D27",
    "border": "#D4CFC6",
    "border_accent": "#C7372F",
}

YORHA_STATUS_LIGHT: dict[str, dict[str, str]] = {
    "submitted": {"text": "#4A4540", "border": "#B8B3AA"},
    "queued": {"text": "#2E7D6E", "border": "#4A9E8E"},
    "in_progress": {"text": "#2A2520", "border": "#C7372F"},
    "review": {"text": "#5E4D7A", "border": "#7E6B9B"},
    "input_required": {"text": "#8B6340", "border": "#B8834A"},
    "blocked": {"text": "#C7372F", "border": "#A02D27"},
    "completed": {"text": "#4A7A3F", "border": "#5C7A52"},
    "failed": {"text": "#C7372F", "border": "#A02D27"},
    "canceled": {"text": "#9A9590", "border": "#B8B3AA"},
    "timed_out": {"text": "#C7372F", "border": "#A02D27"},
}

YORHA_PRIORITY_LIGHT: dict[str, str] = {
    "critical": "#C7372F",
    "high": "#8B6340",
    "medium": "#2A2520",
    "low": "#9A9590",
}

# ---------------------------------------------------------------------------
# CSS templates (shared font import; theme-specific body/card/etc.)
# ---------------------------------------------------------------------------
_CSS_FONT_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2"
    "?family=Rajdhani:wght@300;400;500;600;700&display=swap');"
)

_CSS_SHARED = """
    * { font-family: 'Rajdhani', monospace !important; }
    .q-badge { border-radius: 0 !important; font-family: 'Rajdhani', monospace !important; letter-spacing: 1px; text-transform: uppercase; }
    .q-btn { border-radius: 0 !important; }
    .q-table { border-radius: 0 !important; }
    .q-input .q-field__control { border-radius: 0 !important; }
    .q-linear-progress { border-radius: 0 !important; }
    .q-select .q-field__control { border-radius: 0 !important; }
"""

YORHA_CSS_DARK = (
    _CSS_FONT_IMPORT
    + _CSS_SHARED
    + """
    body { background-color: #0D0D0D !important; color: #DAD4BB !important; }
    .q-card { border-radius: 0 !important; border: 1px solid #333 !important; background: #1A1A1A !important; }
    .q-header { background: #0D0D0D !important; border-bottom: 1px solid #C7372F !important; }
    .q-drawer { background: #111 !important; border-right: 1px solid #333 !important; }
    ::selection { background: #C7372F; color: #DAD4BB; }
    .scanline {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        pointer-events: none; z-index: 9999;
        background: repeating-linear-gradient(
            0deg, transparent, transparent 2px,
            rgba(13,13,13,0.03) 2px, rgba(13,13,13,0.03) 4px
        );
    }
"""
)

YORHA_CSS_LIGHT = (
    _CSS_FONT_IMPORT
    + _CSS_SHARED
    + """
    body { background-color: #F5F0E8 !important; color: #2A2520 !important; }
    .q-card { border-radius: 0 !important; border: 1px solid #D4CFC6 !important; background: #FFFDF8 !important; }
    .q-header { background: #F5F0E8 !important; border-bottom: 1px solid #C7372F !important; }
    .q-drawer { background: #EDE8DF !important; border-right: 1px solid #D4CFC6 !important; }
    ::selection { background: #C7372F; color: #F5F0E8; }
    .scanline {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        pointer-events: none; z-index: 9999;
        background: repeating-linear-gradient(
            0deg, transparent, transparent 2px,
            rgba(245,240,232,0.04) 2px, rgba(245,240,232,0.04) 4px
        );
    }
"""
)

# ---------------------------------------------------------------------------
# Backward-compat aliases (import sites that used YORHA_COLORS directly)
# ---------------------------------------------------------------------------
YORHA_COLORS = YORHA_COLORS_DARK
YORHA_STATUS = YORHA_STATUS_DARK
YORHA_PRIORITY = YORHA_PRIORITY_DARK
YORHA_CSS = YORHA_CSS_DARK


# ---------------------------------------------------------------------------
# Theme persistence helpers
# ---------------------------------------------------------------------------
def get_theme_mode() -> str:
    """Return 'dark' or 'light' from user session storage."""
    from nicegui import app

    try:
        return app.storage.user.get("theme", "dark")
    except Exception:
        return "dark"


def set_theme_mode(mode: str) -> None:
    """Persist the theme choice ('dark' | 'light') into user session storage."""
    from nicegui import app

    app.storage.user["theme"] = mode


# ---------------------------------------------------------------------------
# Dynamic getters (evaluate at render-time based on stored theme)
# ---------------------------------------------------------------------------
def get_colors() -> dict[str, str]:
    """Return the active color palette dict for the current theme."""
    return YORHA_COLORS_LIGHT if get_theme_mode() == "light" else YORHA_COLORS_DARK


def get_status_colors() -> dict[str, dict[str, str]]:
    """Return status color mapping for the current theme."""
    return YORHA_STATUS_LIGHT if get_theme_mode() == "light" else YORHA_STATUS_DARK


def get_priority_colors() -> dict[str, str]:
    """Return priority color mapping for the current theme."""
    return YORHA_PRIORITY_LIGHT if get_theme_mode() == "light" else YORHA_PRIORITY_DARK


# ---------------------------------------------------------------------------
# Theme application
# ---------------------------------------------------------------------------
def apply_yorha_theme() -> None:
    """Inject the correct YoRHa CSS and dark-mode toggle based on stored theme."""
    is_light = get_theme_mode() == "light"
    css = YORHA_CSS_LIGHT if is_light else YORHA_CSS_DARK
    ui.add_head_html(f"<style>{css}</style>")
    dm = ui.dark_mode()
    if is_light:
        dm.disable()
    else:
        dm.enable()
