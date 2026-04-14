"""Main NiceGUI dashboard layout with YoRHa-inspired Tower theme."""

from __future__ import annotations

from pathlib import Path

from nicegui import ui

from arktower.config import Settings
from arktower.core.event_bus import EventBus
from arktower.core.task_service import TaskService
from arktower.store.connection import DatabaseConnection
from arktower.store.migration import MigrationRunner
from arktower.store.sqlite_repository import SqliteTaskRepository
from arktower.web.theme import YORHA_COLORS, apply_yorha_theme

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


def setup_dashboard() -> None:
    """Configure the NiceGUI dashboard with all pages."""

    @ui.page("/")
    def index():
        svc = get_service()
        _layout("Dashboard", "dashboard")
        with ui.column().classes("w-full max-w-6xl mx-auto p-4"):
            from arktower.web.pages.pool_overview import render_pool_overview
            render_pool_overview(svc, navigate_to_task=lambda tid: ui.navigate.to(f"/tasks/{tid}"))

    @ui.page("/tasks")
    def tasks_page():
        svc = get_service()
        _layout("Task Pool", "list")
        with ui.column().classes("w-full max-w-6xl mx-auto p-4"):
            from arktower.web.pages.task_board import render_task_board
            render_task_board(svc, navigate_to_task=lambda tid: ui.navigate.to(f"/tasks/{tid}"))

    @ui.page("/tasks/{task_id}")
    def task_detail_page(task_id: str):
        svc = get_service()
        _layout("Task Detail", "info")
        with ui.column().classes("w-full max-w-6xl mx-auto p-4"):
            from arktower.web.pages.task_detail import render_task_detail
            render_task_detail(svc, task_id, navigate_back=lambda: ui.navigate.to("/tasks"))

    @ui.page("/analytics")
    def analytics_page():
        svc = get_service()
        _layout("Analytics", "analytics")
        with ui.column().classes("w-full max-w-6xl mx-auto p-4"):
            from arktower.web.pages.analytics import render_analytics
            render_analytics(svc)

    @ui.page("/graph")
    def graph_page():
        svc = get_service()
        _layout("Dependencies", "account_tree")
        with ui.column().classes("w-full max-w-6xl mx-auto p-4"):
            from arktower.web.pages.dependency_graph import render_dependency_graph
            render_dependency_graph(svc)


_NAV_ITEMS = [
    ("DASHBOARD", "dashboard", "/"),
    ("TASK POOL", "list", "/tasks"),
    ("ANALYTICS", "analytics", "/analytics"),
    ("DEPENDENCIES", "account_tree", "/graph"),
]


def _layout(title: str, icon: str) -> None:
    """Standard page layout with YoRHa Tower theme."""
    c = YORHA_COLORS
    apply_yorha_theme()

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
        ui.label(f"[{title.upper()}]").style(
            f"color: {c['text_muted']}; font-size: 0.85rem;"
            " letter-spacing: 2px; font-family: 'Rajdhani', monospace;"
        )

    with ui.left_drawer().style(
        f"background: #111; border-right: 1px solid {c['border']};"
    ).props("width=220"):
        ui.label("[NAVIGATION]").style(
            f"color: {c['text_dim']}; font-size: 0.7rem; letter-spacing: 2px;"
            " padding: 12px 16px 4px 16px;"
        )
        for label, _icon, path in _NAV_ITEMS:
            _nav_item(label, path)

        ui.separator().style(f"background: {c['border']}; margin: 12px 0;")
        ui.label("[YoRHa] ArkTower v0.1.0").style(
            f"color: {c['text_dim']}; font-size: 0.65rem;"
            " letter-spacing: 1px; padding: 8px 16px;"
            " font-family: 'Rajdhani', monospace;"
        )
        ui.label("Tower System Active").style(
            f"color: {c['accent']}; font-size: 0.6rem;"
            " letter-spacing: 1px; padding: 0 16px;"
            " font-family: 'Rajdhani', monospace;"
        )

    ui.html('<div class="scanline"></div>')


def _nav_item(label: str, path: str) -> None:
    """Sidebar navigation item styled as a command-menu entry."""
    c = YORHA_COLORS
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
    ui.run(host=host, port=port, title="ArkTower // Tower System", favicon="▮", dark=True)
