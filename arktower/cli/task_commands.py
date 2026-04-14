"""Task subcommands for the ArkTower CLI."""

from __future__ import annotations

import asyncio
from typing import Optional

import typer
from rich.console import Console

from arktower.cli._context import get_repo, get_svc
from arktower.cli.formatters import format_json, format_task_detail, format_task_table
from arktower.core.models import TaskCreate, TaskFilter, TaskPriority, TaskStatus, TaskUpdate, Trigger

app = typer.Typer(name="task", help="Manage tasks in the pool.")
console = Console()


def _run(coro):
    """Run an async coroutine from sync CLI code."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


@app.command("list")
def task_list(
    status: Optional[str] = typer.Option(None, help="Filter by status (comma-separated)"),
    priority: Optional[str] = typer.Option(None, help="Filter by priority (comma-separated)"),
    search: Optional[str] = typer.Option(None, help="Full-text search query"),
    tags: Optional[str] = typer.Option(None, help="Filter by tags (comma-separated)"),
    limit: int = typer.Option(50, help="Max results"),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List tasks in the pool."""
    svc = get_svc()
    filters = TaskFilter(
        status=[TaskStatus(s.strip()) for s in status.split(",")] if status else None,
        priority=[TaskPriority(p.strip()) for p in priority.split(",")] if priority else None,
        tags=[t.strip() for t in tags.split(",")] if tags else None,
        search=search,
        limit=limit,
    )
    tasks = svc.list_tasks(filters)
    if as_json:
        console.print(format_json(tasks))
    else:
        if not tasks:
            console.print("[dim]No tasks found.[/dim]")
            return
        console.print(format_task_table(tasks))


@app.command("create")
def task_create(
    title: str = typer.Argument(..., help="Task title"),
    description: str = typer.Option("", "--description", "-d", help="Task description"),
    priority: str = typer.Option("medium", "--priority", "-p", help="Priority level"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Tags (comma-separated)"),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Create a new task."""
    svc = get_svc()
    create = TaskCreate(
        title=title,
        description=description,
        priority=TaskPriority(priority),
        tags=[t.strip() for t in tags.split(",")] if tags else [],
    )
    task = _run(svc.create_task(create))
    if as_json:
        console.print(format_json(task))
    else:
        console.print(f"[green]Created task:[/green] {task.id}")
        console.print(format_task_detail(task))


@app.command("show")
def task_show(
    task_id: str = typer.Argument(..., help="Task ID"),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Show task details."""
    svc = get_svc()
    try:
        task = svc.get_task(task_id)
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)
    if as_json:
        console.print(format_json(task))
    else:
        console.print(format_task_detail(task))


@app.command("update")
def task_update(
    task_id: str = typer.Argument(..., help="Task ID"),
    title: Optional[str] = typer.Option(None, "--title"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    priority: Optional[str] = typer.Option(None, "--priority", "-p"),
) -> None:
    """Update task fields."""
    svc = get_svc()
    updates_dict: dict = {}
    if title is not None:
        updates_dict["title"] = title
    if description is not None:
        updates_dict["description"] = description
    if priority is not None:
        updates_dict["priority"] = TaskPriority(priority)
    if not updates_dict:
        console.print("[yellow]No updates specified.[/yellow]")
        return
    updates = TaskUpdate(**updates_dict)
    try:
        task = svc.update_task(task_id, updates)
        console.print(f"[green]Updated task:[/green] {task.id}")
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)


@app.command("advance")
def task_advance(
    task_id: str = typer.Argument(..., help="Task ID"),
    trigger: str = typer.Argument(..., help="Trigger name (e.g. enqueue, complete, fail)"),
    actor: str = typer.Option("cli-user", "--actor", "-a"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n"),
) -> None:
    """Advance task state with a trigger."""
    svc = get_svc()
    try:
        task = _run(svc.advance_task(task_id, Trigger(trigger), actor=actor, notes=notes))
        console.print(f"[green]Advanced task {task.id} → {task.status.value}[/green]")
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)


@app.command("claim")
def task_claim(
    task_id: str = typer.Argument(..., help="Task ID"),
    agent_id: str = typer.Argument(..., help="Agent ID to assign"),
) -> None:
    """Claim a task for an agent."""
    svc = get_svc()
    try:
        task = _run(svc.claim_task(task_id, agent_id))
        console.print(f"[green]Claimed task {task.id} by {agent_id}[/green]")
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)


@app.command("complete")
def task_complete(
    task_id: str = typer.Argument(..., help="Task ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o"),
) -> None:
    """Complete a task."""
    svc = get_svc()
    try:
        task = _run(svc.complete_task(task_id, actor="cli-user", output=output))
        console.print(f"[green]Completed task {task.id}[/green]")
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)


@app.command("delete")
def task_delete(
    task_id: str = typer.Argument(..., help="Task ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a task."""
    if not force:
        confirm = typer.confirm(f"Delete task {task_id}?")
        if not confirm:
            raise typer.Abort()
    repo = get_repo()
    if repo.delete(task_id):
        console.print(f"[green]Deleted task {task_id}[/green]")
    else:
        console.print(f"[red]Task not found: {task_id}[/red]")
        raise typer.Exit(1)
