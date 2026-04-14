"""YoRHa-inspired design tokens and global CSS for the ArkTower dashboard."""

from __future__ import annotations

from nicegui import ui

YORHA_COLORS = {
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

YORHA_STATUS = {
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

YORHA_PRIORITY = {
    "critical": "#C7372F",
    "high": "#D4A574",
    "medium": "#DAD4BB",
    "low": "#8A8172",
}

YORHA_CSS = """
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Rajdhani', monospace !important; }
    body { background-color: #0D0D0D !important; color: #DAD4BB !important; }
    .q-card { border-radius: 0 !important; border: 1px solid #333 !important; background: #1A1A1A !important; }
    .q-header { background: #0D0D0D !important; border-bottom: 1px solid #C7372F !important; }
    .q-drawer { background: #111 !important; border-right: 1px solid #333 !important; }
    .q-badge { border-radius: 0 !important; font-family: 'Rajdhani', monospace !important; letter-spacing: 1px; text-transform: uppercase; }
    .q-btn { border-radius: 0 !important; }
    .q-table { border-radius: 0 !important; }
    .q-input .q-field__control { border-radius: 0 !important; }
    .q-linear-progress { border-radius: 0 !important; }
    .q-select .q-field__control { border-radius: 0 !important; }
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


def apply_yorha_theme() -> None:
    """Inject YoRHa CSS and enable dark mode globally."""
    ui.add_head_html(f"<style>{YORHA_CSS}</style>")
    ui.dark_mode().enable()
