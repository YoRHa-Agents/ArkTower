"""Analytics page — YoRHa-styled completion trends and queue health."""

from __future__ import annotations

from nicegui import ui

from arktower.core.task_service import TaskService
from arktower.web.i18n import t
from arktower.web.theme import get_colors


def render_analytics(svc: TaskService) -> None:
    """Render the analytics page."""
    c = get_colors()
    stats = svc.get_stats()

    ui.label(t("analytics.title")).style(
        f"color: {c['text_muted']}; font-size: 0.85rem; letter-spacing: 2px;"
        " font-family: 'Rajdhani', monospace; margin-bottom: 16px;"
    )

    with ui.row().classes("w-full gap-4"):
        with ui.card().style(
            f"flex: 1; background: {c['bg_surface']}; border: 1px solid {c['border']}; border-radius: 0;"
        ):
            ui.label(t("analytics.completion")).style(
                f"color: {c['text_dim']}; font-size: 0.7rem; letter-spacing: 2px;"
                " font-family: 'Rajdhani', monospace; margin-bottom: 8px;"
            )
            completed = stats.by_status.get("completed", 0)
            failed = stats.by_status.get("failed", 0)
            total_terminal = (
                completed
                + failed
                + stats.by_status.get("canceled", 0)
                + stats.by_status.get("timed_out", 0)
            )
            if total_terminal > 0:
                rate = completed / total_terminal * 100
                rate_color = "#8BAA7F" if rate >= 80 else c["accent"] if rate < 50 else "#D4A574"
                ui.label(f"{rate:.1f}%").style(
                    f"color: {rate_color}; font-size: 3rem; font-weight: 700;"
                    " font-family: 'Rajdhani', monospace; line-height: 1;"
                )
                ui.label(t("analytics.success_rate")).style(
                    f"color: {c['text_dim']}; font-size: 0.7rem; letter-spacing: 2px;"
                    " font-family: 'Rajdhani', monospace;"
                )
            else:
                ui.label(t("analytics.no_data")).style(
                    f"color: {c['text_dim']}; font-family: 'Rajdhani', monospace;"
                    " letter-spacing: 1px;"
                )
                ui.label(t("analytics.no_tasks")).style(
                    f"color: {c['text_dim']}; font-size: 0.8rem;"
                )

            if stats.avg_completion_seconds is not None:
                mins = stats.avg_completion_seconds / 60
                ui.label(f"{mins:.1f} MIN").style(
                    f"color: {c['text_primary']}; font-size: 1.4rem; font-weight: 600;"
                    " font-family: 'Rajdhani', monospace; margin-top: 12px;"
                )
                ui.label(t("analytics.avg_time")).style(
                    f"color: {c['text_dim']}; font-size: 0.7rem; letter-spacing: 2px;"
                    " font-family: 'Rajdhani', monospace;"
                )

        with ui.card().style(
            f"flex: 1; background: {c['bg_surface']}; border: 1px solid {c['border']}; border-radius: 0;"
        ):
            ui.label(t("analytics.queue_health")).style(
                f"color: {c['text_dim']}; font-size: 0.7rem; letter-spacing: 2px;"
                " font-family: 'Rajdhani', monospace; margin-bottom: 8px;"
            )
            queued = stats.by_status.get("queued", 0)
            in_progress = stats.by_status.get("in_progress", 0)

            _queue_metric(t("analytics.queued"), str(queued), "#7FDBCA")
            _queue_metric(t("analytics.in_progress"), str(in_progress), c["text_primary"])

            if stats.oldest_queued_age_seconds is not None:
                age_mins = stats.oldest_queued_age_seconds / 60
                color = c["accent"] if age_mins > 60 else "#D4A574" if age_mins > 15 else "#8BAA7F"
                _queue_metric(t("analytics.oldest"), f"{age_mins:.0f} MIN", color)


def _queue_metric(label: str, value: str, color: str) -> None:
    """Render a single queue health metric line."""
    c = get_colors()
    with ui.row().classes("items-center gap-3 mt-2"):
        ui.label(value).style(
            f"color: {color}; font-size: 1.4rem; font-weight: 600;"
            " font-family: 'Rajdhani', monospace; min-width: 60px;"
        )
        ui.label(label).style(
            f"color: {c['text_dim']}; font-size: 0.7rem; letter-spacing: 2px;"
            " font-family: 'Rajdhani', monospace;"
        )
