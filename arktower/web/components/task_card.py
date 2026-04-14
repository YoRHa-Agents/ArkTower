"""YoRHa-styled task card widget for pool views."""

from __future__ import annotations

from nicegui import ui

from arktower.core.models import Task
from arktower.web.components.status_badge import priority_indicator, status_badge
from arktower.web.theme import get_colors


def task_card(task: Task, on_click=None) -> ui.card:
    """Render a NieR:Automata-styled summary card for a task."""
    c = get_colors()
    with ui.card().classes("w-full cursor-pointer").style(
        f"background: {c['bg_surface']}; border: 1px solid {c['border']};"
        " border-radius: 0; transition: border-color 0.2s;"
    ) as card:
        card.on(
            "mouseover",
            js_handler=f"(e) => e.currentTarget.style.borderColor = '{c['accent']}'",
        )
        card.on(
            "mouseout",
            js_handler=f"(e) => e.currentTarget.style.borderColor = '{c['border']}'",
        )
        if on_click:
            card.on("click", lambda: on_click(task.id))

        with ui.row().classes("w-full justify-between items-center"):
            with ui.row().classes("items-center gap-2"):
                ui.label(f"ATK-{task.id[:8]}").style(
                    f"color: {c['text_dim']}; font-family: 'Rajdhani', monospace;"
                    " font-size: 0.7rem; letter-spacing: 1px;"
                )
                ui.label(task.title.upper()).style(
                    f"color: {c['text_primary']}; font-size: 1.05rem;"
                    " font-weight: 600; letter-spacing: 0.5px;"
                ).classes("truncate")
            status_badge(task.status.value)

        with ui.row().classes("w-full items-center gap-2 mt-1"):
            priority_indicator(task.priority.value)
            if task.assigned_to:
                ui.label(f"// {task.assigned_to}").style(
                    f"color: {c['text_muted']}; font-size: 0.75rem;"
                    " font-family: 'Rajdhani', monospace;"
                )

        if task.tags:
            with ui.row().classes("gap-1 mt-1 flex-wrap"):
                for tag in task.tags[:5]:
                    ui.label(tag.upper()).style(
                        f"color: {c['text_dim']}; border: 1px solid {c['border']};"
                        " font-size: 0.65rem; padding: 1px 6px;"
                        " font-family: 'Rajdhani', monospace; letter-spacing: 1px;"
                    )

    return card
