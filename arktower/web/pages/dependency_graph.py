"""Dependency graph page — YoRHa-styled DAG visualization of task dependencies."""

from __future__ import annotations

from nicegui import ui

from arktower.core.models import TaskFilter
from arktower.core.task_service import TaskService
from arktower.web.components.status_badge import STATUS_COLORS
from arktower.web.theme import YORHA_COLORS


def render_dependency_graph(svc: TaskService) -> None:
    """Render a dependency graph using Mermaid with YoRHa dark theme."""
    c = YORHA_COLORS
    tasks = svc.list_tasks(TaskFilter(limit=100))
    repo = svc._repo

    mermaid_lines = [
        "%%{init: {'theme': 'dark', 'themeVariables': {"
        "'primaryColor': '#1A1A1A', 'primaryTextColor': '#DAD4BB',"
        "'primaryBorderColor': '#333', 'lineColor': '#555',"
        "'secondaryColor': '#242424', 'tertiaryColor': '#0D0D0D'"
        "}}}%%",
        "graph TD",
    ]
    for task in tasks:
        colors = STATUS_COLORS.get(task.status.value, {"border": "#555"})
        short_id = task.id[:8]
        label = task.title[:30].replace('"', "'")
        mermaid_lines.append(f'    {short_id}["{label}"]')
        mermaid_lines.append(f"    style {short_id} stroke:{colors['border']},fill:#1A1A1A,color:#DAD4BB")

        deps = repo.get_dependencies(task.id)
        for dep in deps:
            dep_short = dep.to_task_id[:8]
            mermaid_lines.append(f"    {short_id} --> {dep_short}")

    ui.label("[TOPOLOGY] DEPENDENCY GRAPH").style(
        f"color: {c['text_muted']}; font-size: 0.85rem; letter-spacing: 2px;"
        " font-family: 'Rajdhani', monospace; margin-bottom: 16px;"
    )

    if len(tasks) == 0:
        ui.label("[NO DATA] No tasks to display.").style(
            f"color: {c['text_dim']}; font-family: 'Rajdhani', monospace;"
            " letter-spacing: 1px;"
        )
    else:
        mermaid_code = "\n".join(mermaid_lines)
        ui.mermaid(mermaid_code).classes("w-full")
