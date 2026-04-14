"""Task detail page — YoRHa-styled full task view with history timeline."""

from __future__ import annotations

from nicegui import ui

from arktower.core.models import TaskEvent
from arktower.core.task_service import TaskService
from arktower.web.components.status_badge import STATUS_COLORS, priority_indicator, status_badge
from arktower.web.theme import YORHA_COLORS


def render_task_detail(svc: TaskService, task_id: str, navigate_back=None) -> None:
    """Render the detail view for a single task."""
    c = YORHA_COLORS

    try:
        task = svc.get_task(task_id)
    except Exception:
        ui.label("[ERROR] Task not found").style(
            f"color: {c['accent']}; font-family: 'Rajdhani', monospace;"
            " letter-spacing: 1px; font-size: 1.2rem;"
        )
        return

    if navigate_back:
        ui.button("< BACK TO POOL", on_click=navigate_back).props("flat").style(
            f"color: {c['text_muted']}; border: 1px solid {c['border']};"
            " border-radius: 0; letter-spacing: 1px;"
            " font-family: 'Rajdhani', monospace; font-size: 0.8rem;"
        )

    with ui.row().classes("w-full items-center gap-4 mt-2"):
        ui.label(f"ATK-{task.id[:8]} // {task.title.upper()}").style(
            f"color: {c['text_primary']}; font-size: 1.4rem; font-weight: 600;"
            " letter-spacing: 1px; font-family: 'Rajdhani', monospace; flex: 1;"
        )
        status_badge(task.status.value)
        priority_indicator(task.priority.value)

    with ui.card().classes("w-full mt-2").style(
        f"background: {c['bg_surface']}; border: 1px solid {c['border']}; border-radius: 0;"
    ):
        with ui.grid(columns=3).classes("w-full gap-4"):
            _field("[ID]", task.id, mono=True)
            _field("[OWNER]", task.owner_id)
            _field("[ASSIGNED]", task.assigned_to or "—")
            _field("[CREATED]", str(task.created_at)[:19])
            _field("[UPDATED]", str(task.updated_at)[:19])
            _field("[COMPLETED]", str(task.completed_at)[:19] if task.completed_at else "—")
            _field("[TAGS]", ", ".join(t.upper() for t in task.tags) if task.tags else "—")
            _field("[TEMPLATE]", task.template_id or "—")
            _field("[VERSION]", str(task.version))

    if task.description:
        with ui.card().classes("w-full mt-2").style(
            f"background: {c['bg_surface']}; border: 1px solid {c['border']}; border-radius: 0;"
        ):
            ui.label("[DESCRIPTION]").style(
                f"color: {c['text_dim']}; font-size: 0.7rem; letter-spacing: 2px;"
                " font-family: 'Rajdhani', monospace; margin-bottom: 4px;"
            )
            ui.markdown(task.description).classes("prose prose-invert max-w-none").style(
                f"color: {c['text_primary']};"
            )

    if task.output:
        with ui.card().classes("w-full mt-2").style(
            f"background: {c['bg_surface']}; border: 1px solid {c['border']}; border-radius: 0;"
        ):
            ui.label("[OUTPUT]").style(
                f"color: {c['text_dim']}; font-size: 0.7rem; letter-spacing: 2px;"
                " font-family: 'Rajdhani', monospace; margin-bottom: 4px;"
            )
            ui.code(task.output).classes("w-full")

    if task.error:
        with ui.card().classes("w-full mt-2").style(
            f"background: {c['bg_surface']}; border: 1px solid {c['accent']}; border-radius: 0;"
        ):
            ui.label("[ERROR]").style(
                f"color: {c['accent']}; font-size: 0.7rem; letter-spacing: 2px;"
                " font-family: 'Rajdhani', monospace; margin-bottom: 4px;"
            )
            ui.code(task.error).classes("w-full")

    history = svc.get_task_history(task_id)
    if history:
        with ui.card().classes("w-full mt-2").style(
            f"background: {c['bg_surface']}; border: 1px solid {c['border']}; border-radius: 0;"
        ):
            ui.label("[LOG] TRANSITION HISTORY").style(
                f"color: {c['text_dim']}; font-size: 0.7rem; letter-spacing: 2px;"
                " font-family: 'Rajdhani', monospace; margin-bottom: 8px;"
            )
            for event in reversed(history):
                _history_entry(event)


def _field(label: str, value: str, mono: bool = False) -> None:
    """Render a labeled data field in YoRHa style."""
    c = YORHA_COLORS
    with ui.column().classes("gap-0"):
        ui.label(label).style(
            f"color: {c['text_dim']}; font-size: 0.65rem; letter-spacing: 2px;"
            " font-family: 'Rajdhani', monospace;"
        )
        style = (
            f"color: {c['text_primary']}; font-size: 0.85rem;"
            " font-family: 'Rajdhani', monospace;"
        )
        if mono:
            style += " letter-spacing: 0.5px;"
        ui.label(value).style(style)


def _history_entry(event: TaskEvent) -> None:
    """Render a single history event in military log format."""
    c = YORHA_COLORS
    from_colors = STATUS_COLORS.get(event.from_status.value, {"text": "#8A8172"})
    to_colors = STATUS_COLORS.get(event.to_status.value, {"text": "#8A8172"})
    actor_part = f" // {event.actor}" if event.actor else ""

    with ui.row().classes("items-center gap-2 py-1").style(
        f"border-bottom: 1px solid {c['bg_elevated']};"
    ):
        ui.label(f"[{str(event.timestamp)[:19]}]").style(
            f"color: {c['text_dim']}; font-family: 'Rajdhani', monospace;"
            " font-size: 0.75rem; width: 160px; letter-spacing: 0.5px;"
        )
        ui.label(event.trigger.value.upper()).style(
            f"color: {c['text_muted']}; font-family: 'Rajdhani', monospace;"
            " font-size: 0.75rem; font-weight: 600; width: 100px;"
            " letter-spacing: 1px;"
        )
        ui.label(event.from_status.value.upper()).style(
            f"color: {from_colors['text']}; font-family: 'Rajdhani', monospace;"
            " font-size: 0.75rem;"
        )
        ui.label("→").style(
            f"color: {c['text_dim']}; font-size: 0.75rem;"
        )
        ui.label(event.to_status.value.upper()).style(
            f"color: {to_colors['text']}; font-family: 'Rajdhani', monospace;"
            " font-size: 0.75rem;"
        )
        if actor_part:
            ui.label(actor_part).style(
                f"color: {c['text_dim']}; font-family: 'Rajdhani', monospace;"
                " font-size: 0.7rem;"
            )
