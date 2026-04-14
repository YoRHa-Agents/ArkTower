"""Dependency graph page — YoRHa-styled DAG visualization of task dependencies."""

from __future__ import annotations

from nicegui import ui

from arktower.core.models import TaskFilter
from arktower.core.task_service import TaskService
from arktower.web.i18n import t
from arktower.web.theme import get_colors, get_status_colors, get_theme_mode


def render_dependency_graph(svc: TaskService) -> None:
    """Render a dependency graph using Mermaid with YoRHa theming."""
    c = get_colors()
    tasks = svc.list_tasks(TaskFilter(limit=100))
    repo = svc._repo

    is_light = get_theme_mode() == "light"
    mermaid_theme = "default" if is_light else "dark"
    node_fill = c["bg_surface"]
    node_text = c["text_primary"]
    node_border = c["border"]
    line_color = c["text_dim"]

    mermaid_lines = [
        f"%%{{init: {{'theme': '{mermaid_theme}', 'themeVariables': {{"
        f"'primaryColor': '{node_fill}', 'primaryTextColor': '{node_text}',"
        f"'primaryBorderColor': '{node_border}', 'lineColor': '{line_color}',"
        f"'secondaryColor': '{c['bg_elevated']}', 'tertiaryColor': '{c['bg_primary']}'"
        "}}}}%%",
        "graph TD",
    ]
    status_colors = get_status_colors()
    for task in tasks:
        colors = status_colors.get(task.status.value, {"border": c["border"]})
        short_id = task.id[:8]
        label = task.title[:30].replace('"', "'")
        mermaid_lines.append(f'    {short_id}["{label}"]')
        mermaid_lines.append(
            f"    style {short_id} stroke:{colors['border']},fill:{node_fill},color:{node_text}"
        )

        deps = repo.get_dependencies(task.id)
        for dep in deps:
            dep_short = dep.to_task_id[:8]
            mermaid_lines.append(f"    {short_id} --> {dep_short}")

    ui.label(t("graph.title")).style(
        f"color: {c['text_muted']}; font-size: 0.85rem; letter-spacing: 2px;"
        " font-family: 'Rajdhani', monospace; margin-bottom: 16px;"
    )

    if len(tasks) == 0:
        ui.label(t("graph.empty")).style(
            f"color: {c['text_dim']}; font-family: 'Rajdhani', monospace;"
            " letter-spacing: 1px;"
        )
    else:
        mermaid_code = "\n".join(mermaid_lines)
        ui.mermaid(mermaid_code).classes("w-full")
