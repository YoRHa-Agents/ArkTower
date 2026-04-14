"""Root Typer CLI: combines subcommands and initializes storage on startup."""

from __future__ import annotations

import typer

from arktower.cli.deps import ensure_cli_initialized, reset_cli_state
from arktower.cli import eval_commands, pool_commands, server_commands, task_commands

app = typer.Typer(
    name="arktower",
    help="ArkTower — task pool CLI",
    no_args_is_help=True,
)


@app.callback()
def _cli_callback() -> None:
    """Initialize SQLite and apply migrations before any subcommand runs."""
    ensure_cli_initialized()


app.add_typer(task_commands.app, name="task")
app.add_typer(pool_commands.app, name="pool")
app.add_typer(server_commands.app, name="server")
app.add_typer(eval_commands.app, name="eval")


@app.command("version")
def version() -> None:
    """Show the ArkTower version."""
    from arktower import __version__

    typer.echo(f"ArkTower v{__version__}")


__all__ = ["app", "reset_cli_state"]
