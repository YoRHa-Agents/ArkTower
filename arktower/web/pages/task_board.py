"""Task board page — YoRHa-styled filterable task list with search."""

from __future__ import annotations

from nicegui import ui

from arktower.core.models import TaskFilter, TaskPriority, TaskStatus
from arktower.core.task_service import TaskService
from arktower.web.components.task_card import task_card
from arktower.web.i18n import t
from arktower.web.theme import get_colors


def render_task_board(svc: TaskService, navigate_to_task=None) -> None:
    """Render the filterable task board."""
    c = get_colors()

    _input_style = (
        f"color: {c['text_primary']}; background: {c['bg_surface']};"
        f" border: 1px solid {c['border']};"
        " border-radius: 0; font-family: 'Rajdhani', monospace;"
    )

    ui.label(t("board.title")).style(
        f"color: {c['text_muted']}; font-size: 0.8rem; letter-spacing: 2px;"
        " font-family: 'Rajdhani', monospace; margin-bottom: 8px;"
    )

    search_input = (
        ui.input(placeholder=t("board.search"))
        .props("outlined dense clearable")
        .classes("w-full")
        .style(_input_style)
    )

    with ui.row().classes("w-full gap-2 items-center flex-wrap"):
        status_select = (
            ui.select(
                options={s.value: f"[{s.value.upper()}]" for s in TaskStatus},
                label=t("board.status"),
                multiple=True,
            )
            .props("outlined dense clearable")
            .classes("min-w-[160px]")
            .style(_input_style)
        )

        priority_select = (
            ui.select(
                options={p.value: f"[{p.value.upper()}]" for p in TaskPriority},
                label=t("board.priority"),
                multiple=True,
            )
            .props("outlined dense clearable")
            .classes("min-w-[140px]")
            .style(_input_style)
        )

        refresh_btn = (
            ui.button(t("board.refresh"), icon="refresh")
            .props("flat dense")
            .style(
                f"color: {c['text_muted']}; border: 1px solid {c['border']};"
                " border-radius: 0; letter-spacing: 1px;"
                " font-family: 'Rajdhani', monospace;"
            )
        )

    task_container = ui.column().classes("w-full gap-2 mt-2")

    async def load_tasks():
        task_container.clear()
        status_vals = status_select.value if status_select.value else None
        priority_vals = priority_select.value if priority_select.value else None
        filters = TaskFilter(
            status=[TaskStatus(s) for s in status_vals] if status_vals else None,
            priority=[TaskPriority(p) for p in priority_vals] if priority_vals else None,
            search=search_input.value if search_input.value else None,
            limit=50,
        )
        tasks = svc.list_tasks(filters)
        with task_container:
            if not tasks:
                ui.label(t("board.empty")).style(
                    f"color: {c['text_dim']}; font-family: 'Rajdhani', monospace;"
                    " letter-spacing: 1px; padding: 32px 0; text-align: center;"
                ).classes("w-full")
            else:
                for task in tasks:
                    task_card(task, on_click=navigate_to_task)

    refresh_btn.on("click", load_tasks)
    search_input.on("keyup.enter", load_tasks)
    ui.timer(0.1, load_tasks, once=True)
