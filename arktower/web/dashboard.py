"""Main NiceGUI dashboard layout with YoRHa-inspired Tower theme."""

from __future__ import annotations

from pathlib import Path

from nicegui import app, ui

from arktower.config import Settings
from arktower.core.event_bus import EventBus
from arktower.core.task_service import TaskService
from arktower.store.connection import DatabaseConnection
from arktower.store.migration import MigrationRunner
from arktower.store.sqlite_repository import SqliteTaskRepository
from arktower.web.i18n import get_lang, set_lang, t
from arktower.web.theme import (
    apply_yorha_theme,
    get_colors,
    get_theme_mode,
    set_theme_mode,
)

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def _boot_service() -> TaskService:
    """Initialize database and return a TaskService instance."""
    settings = Settings()
    db = DatabaseConnection(settings.db_path)
    db.connect()
    if MIGRATIONS_DIR.is_dir():
        MigrationRunner(db, MIGRATIONS_DIR).run_migrations()
    repo = SqliteTaskRepository(db)
    bus = EventBus()
    return TaskService(repo, bus)


_svc: TaskService | None = None


def get_service() -> TaskService:
    global _svc
    if _svc is None:
        _svc = _boot_service()
    return _svc


def _mount_api_routes() -> None:
    """Mount the FastAPI REST API routes on the NiceGUI server."""
    from arktower.api.rest_routes import router as api_router
    from arktower.api.ws_manager import ConnectionManager
    from arktower.core.event_bus import EventBus

    bus = EventBus()
    app.state.event_bus = bus
    app.state.ws_manager = ConnectionManager(bus)
    app.include_router(api_router)


def setup_dashboard() -> None:
    """Configure the NiceGUI dashboard with all pages and REST API."""
    _mount_api_routes()

    @ui.page("/")
    def index():
        svc = get_service()
        _layout("nav.dashboard", "dashboard")
        with ui.column().classes("w-full max-w-6xl mx-auto p-4"):
            from arktower.web.pages.pool_overview import render_pool_overview

            render_pool_overview(svc, navigate_to_task=lambda tid: ui.navigate.to(f"/tasks/{tid}"))

    @ui.page("/tasks")
    def tasks_page():
        svc = get_service()
        _layout("nav.task_pool", "list")
        with ui.column().classes("w-full max-w-6xl mx-auto p-4"):
            from arktower.web.pages.task_board import render_task_board

            render_task_board(svc, navigate_to_task=lambda tid: ui.navigate.to(f"/tasks/{tid}"))

    @ui.page("/tasks/{task_id}")
    def task_detail_page(task_id: str):
        svc = get_service()
        _layout("nav.task_pool", "info")
        with ui.column().classes("w-full max-w-6xl mx-auto p-4"):
            from arktower.web.pages.task_detail import render_task_detail

            render_task_detail(svc, task_id, navigate_back=lambda: ui.navigate.to("/tasks"))

    @ui.page("/analytics")
    def analytics_page():
        svc = get_service()
        _layout("nav.analytics", "analytics")
        with ui.column().classes("w-full max-w-6xl mx-auto p-4"):
            from arktower.web.pages.analytics import render_analytics

            render_analytics(svc)

    @ui.page("/graph")
    def graph_page():
        svc = get_service()
        _layout("nav.dependencies", "account_tree")
        with ui.column().classes("w-full max-w-6xl mx-auto p-4"):
            from arktower.web.pages.dependency_graph import render_dependency_graph

            render_dependency_graph(svc)


_NAV_KEYS = [
    ("nav.dashboard", "dashboard", "/"),
    ("nav.task_pool", "list", "/tasks"),
    ("nav.analytics", "analytics", "/analytics"),
    ("nav.dependencies", "account_tree", "/graph"),
]


def _toggle_lang() -> None:
    """Flip between EN and ZH, then reload."""
    new = "zh" if get_lang() == "en" else "en"
    set_lang(new)
    ui.navigate.to(app.storage.user.get("_last_path", "/"))


def _toggle_theme() -> None:
    """Flip between dark and light, then reload."""
    new = "light" if get_theme_mode() == "dark" else "dark"
    set_theme_mode(new)
    ui.navigate.to(app.storage.user.get("_last_path", "/"))


def _layout(title_key: str, icon: str) -> None:
    """Standard page layout with YoRHa Tower theme."""
    c = get_colors()
    apply_yorha_theme()

    # Persist current path for post-toggle reload
    app.storage.user["_last_path"] = ui.context.client.page.path

    with ui.header().style(
        f"background: {c['bg_primary']}; border-bottom: 1px solid {c['accent']};"
    ).classes("items-center justify-between"):
        with ui.row().classes("items-center gap-3"):
            ui.label("▮").style(f"color: {c['accent']}; font-size: 1.5rem;")
            ui.label("ARKTOWER").style(
                f"color: {c['text_primary']}; font-size: 1.25rem; font-weight: 700;"
                " letter-spacing: 4px; text-transform: uppercase;"
                " font-family: 'Rajdhani', monospace;"
            )
        with ui.row().classes("items-center gap-2"):
            ui.label(f"[{t(title_key).upper()}]").style(
                f"color: {c['text_muted']}; font-size: 0.85rem;"
                " letter-spacing: 2px; font-family: 'Rajdhani', monospace;"
            )
            # Language toggle
            lang_label = "中" if get_lang() == "en" else "EN"
            ui.button(lang_label, on_click=_toggle_lang).props("flat dense").style(
                f"color: {c['text_muted']}; border: 1px solid {c['border']};"
                " border-radius: 0; font-family: 'Rajdhani', monospace;"
                " min-width: 36px; font-size: 0.8rem; letter-spacing: 1px;"
            )
            # Theme toggle
            theme_icon = "light_mode" if get_theme_mode() == "dark" else "dark_mode"
            ui.button(icon=theme_icon, on_click=_toggle_theme).props("flat dense").style(
                f"color: {c['text_muted']}; border: 1px solid {c['border']};"
                " border-radius: 0; min-width: 36px;"
            )

    drawer_bg = "#111" if get_theme_mode() == "dark" else c["bg_elevated"]
    with ui.left_drawer().style(
        f"background: {drawer_bg}; border-right: 1px solid {c['border']};"
    ).props("width=220"):
        ui.label(t("nav.navigation")).style(
            f"color: {c['text_dim']}; font-size: 0.7rem; letter-spacing: 2px;"
            " padding: 12px 16px 4px 16px;"
        )
        for key, _icon, path in _NAV_KEYS:
            _nav_item(t(key), path)

        ui.separator().style(f"background: {c['border']}; margin: 12px 0;")
        ui.label(t("footer.system")).style(
            f"color: {c['text_dim']}; font-size: 0.65rem;"
            " letter-spacing: 1px; padding: 8px 16px;"
            " font-family: 'Rajdhani', monospace;"
        )
        ui.label(t("footer.status")).style(
            f"color: {c['accent']}; font-size: 0.6rem;"
            " letter-spacing: 1px; padding: 0 16px;"
            " font-family: 'Rajdhani', monospace;"
        )

    ui.html('<div class="scanline"></div>')


def _nav_item(label: str, path: str) -> None:
    """Sidebar navigation item styled as a command-menu entry."""
    c = get_colors()
    with ui.row().classes("items-center gap-2 w-full").style(
        f"padding: 8px 16px; cursor: pointer; transition: background 0.15s;"
        f" color: {c['text_muted']};"
    ).on("click", lambda: ui.navigate.to(path)) as row:
        row.on(
            "mouseover",
            js_handler=f"(e) => {{ e.currentTarget.style.background = '{c['bg_elevated']}'; e.currentTarget.style.color = '{c['text_primary']}'; }}",
        )
        row.on(
            "mouseout",
            js_handler=f"(e) => {{ e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '{c['text_muted']}'; }}",
        )
        ui.label(">").style(
            f"color: {c['accent']}; font-family: 'Rajdhani', monospace; font-size: 0.85rem;"
        )
        ui.label(label).style(
            "font-family: 'Rajdhani', monospace; font-size: 0.85rem;"
            " letter-spacing: 2px; text-transform: uppercase;"
        )


def run_dashboard(host: str = "0.0.0.0", port: int = 8080) -> None:
    """Start the NiceGUI dashboard server."""
    setup_dashboard()
    ui.run(
        host=host,
        port=port,
        title="ArkTower // Tower System",
        favicon="▮",
        dark=True,
        storage_secret="arktower-yorha-storage-key",
    )
