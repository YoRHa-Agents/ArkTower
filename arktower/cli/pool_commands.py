"""Pool subcommands for the ArkTower CLI."""

from __future__ import annotations

import typer
from rich.console import Console

from arktower.cli._context import get_svc
from arktower.cli.formatters import format_json, format_stats, format_task_detail

app = typer.Typer(name="pool", help="Pool-level operations.")
console = Console()


@app.command("stats")
def pool_stats(
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Show pool statistics."""
    svc = get_svc()
    stats = svc.get_stats()
    if as_json:
        console.print(format_json(stats))
    else:
        console.print(format_stats(stats))


@app.command("next")
def pool_next(
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Get the next available task (highest priority queued)."""
    svc = get_svc()
    task = svc.get_next_task()
    if task is None:
        console.print("[dim]No queued tasks available.[/dim]")
        return
    if as_json:
        console.print(format_json(task))
    else:
        console.print("[bold]Next task:[/bold]")
        console.print(format_task_detail(task))
