"""Pool overview page — YoRHa-styled metrics dashboard and task summary."""

from __future__ import annotations

from nicegui import ui

from arktower.core.models import TaskFilter
from arktower.core.task_service import TaskService
from arktower.web.components.task_card import task_card
from arktower.web.i18n import t
from arktower.web.theme import get_colors, get_priority_colors, get_status_colors


def render_pool_overview(svc: TaskService, navigate_to_task=None) -> None:
    """Render the main pool overview page."""
    c = get_colors()
    stats = svc.get_stats()

    _section_header(t("pool.system_status"))

    with ui.row().classes("w-full gap-4 flex-wrap"):
        _metric_card(t("pool.total_tasks"), str(stats.total), c["text_primary"])
        active = sum(
            stats.by_status.get(s, 0)
            for s in ["submitted", "queued", "in_progress", "review", "input_required"]
        )
        _metric_card(t("pool.active"), str(active), c["info"])
        blocked = stats.by_status.get("blocked", 0)
        _metric_card(t("pool.blocked"), str(blocked), c["accent"])
        failed = stats.by_status.get("failed", 0)
        _metric_card(t("pool.failed"), str(failed), c["accent"])

    with ui.row().classes("w-full gap-4 mt-4"):
        with ui.card().style(
            f"flex: 1; background: {c['bg_surface']}; border: 1px solid {c['border']}; border-radius: 0;"
        ):
            _section_header(t("pool.status_dist"), inline=True)
            if stats.by_status:
                status_colors = get_status_colors()
                for status, count in sorted(stats.by_status.items(), key=lambda x: -x[1]):
                    colors = status_colors.get(status, {"text": c["text_dim"], "border": c["border"]})
                    with ui.row().classes("items-center gap-2"):
                        ui.label(f"[{status.upper()}]").style(
                            f"width: 140px; color: {colors['text']}; font-size: 0.8rem;"
                            " font-family: 'Rajdhani', monospace; letter-spacing: 1px;"
                        )
                        with ui.element("div").style(
                            f"flex: 1; height: 4px; background: {c['bg_elevated']}; position: relative;"
                        ):
                            pct = count / max(stats.total, 1) * 100
                            ui.element("div").style(
                                f"width: {pct}%; height: 100%; background: {colors['border']};"
                                " position: absolute; top: 0; left: 0;"
                            )
                        ui.label(str(count)).style(
                            f"color: {c['text_primary']}; font-family: 'Rajdhani', monospace;"
                            " font-size: 0.85rem; width: 32px; text-align: right;"
                        )
            else:
                ui.label(t("pool.no_data")).style(
                    f"color: {c['text_dim']}; font-family: 'Rajdhani', monospace;"
                )

        with ui.card().style(
            f"flex: 1; background: {c['bg_surface']}; border: 1px solid {c['border']}; border-radius: 0;"
        ):
            _section_header(t("pool.priority_breakdown"), inline=True)
            pri_colors = get_priority_colors()
            for p in ["critical", "high", "medium", "low"]:
                count = stats.by_priority.get(p, 0)
                color = pri_colors.get(p, c["text_dim"])
                if count > 0 or stats.total > 0:
                    with ui.row().classes("items-center gap-2"):
                        ui.label("■").style(f"color: {color}; font-size: 8px;")
                        ui.label(f"[{p.upper()}]").style(
                            f"width: 90px; color: {color}; font-size: 0.8rem;"
                            " font-family: 'Rajdhani', monospace; letter-spacing: 1px;"
                        )
                        with ui.element("div").style(
                            f"flex: 1; height: 4px; background: {c['bg_elevated']}; position: relative;"
                        ):
                            pct = count / max(stats.total, 1) * 100
                            ui.element("div").style(
                                f"width: {pct}%; height: 100%; background: {color};"
                                " position: absolute; top: 0; left: 0;"
                            )
                        ui.label(str(count)).style(
                            f"color: {c['text_primary']}; font-family: 'Rajdhani', monospace;"
                            " font-size: 0.85rem; width: 32px; text-align: right;"
                        )

    recent = svc.list_tasks(TaskFilter(limit=5))
    if recent:
        _section_header(t("pool.recent_feed"))
        for task in recent:
            task_card(task, on_click=navigate_to_task)


def _metric_card(title: str, value: str, color: str) -> None:
    """Render a single YoRHa metric card."""
    c = get_colors()
    with ui.card().style(
        f"flex: 1; min-width: 160px; background: {c['bg_surface']};"
        f" border: 1px solid {c['border']}; border-radius: 0;"
    ).classes("items-center"):
        ui.label(value).style(
            f"color: {color}; font-size: 2.2rem; font-weight: 700;"
            " font-family: 'Rajdhani', monospace; line-height: 1;"
        )
        ui.label(title).style(
            f"color: {c['text_dim']}; font-size: 0.7rem; letter-spacing: 2px;"
            " font-family: 'Rajdhani', monospace; text-transform: uppercase;"
        )


def _section_header(text: str, inline: bool = False) -> None:
    """Render a YoRHa-style section header."""
    c = get_colors()
    cls = "mb-2" if inline else "mt-4 mb-2"
    ui.label(text).classes(cls).style(
        f"color: {c['text_muted']}; font-size: 0.8rem; letter-spacing: 2px;"
        " font-family: 'Rajdhani', monospace; text-transform: uppercase;"
    )
