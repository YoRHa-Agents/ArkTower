"""Server subcommands for the ArkTower CLI."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(name="server", help="Server management commands.")
console = Console()


@app.command("start")
def server_start(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Bind host"),
    port: int = typer.Option(8080, "--port", "-p", help="Bind port"),
    mode: str = typer.Option("dashboard", help="Mode: 'dashboard' (NiceGUI) or 'api' (FastAPI only)"),
) -> None:
    """Start the ArkTower server (dashboard or API-only)."""
    if mode == "dashboard":
        console.print(f"[bold green]Starting ArkTower dashboard on {host}:{port}[/bold green]")
        from arktower.web.dashboard import run_dashboard
        run_dashboard(host=host, port=port)
    elif mode == "api":
        import uvicorn
        console.print(f"[bold green]Starting ArkTower API on {host}:{port}[/bold green]")
        uvicorn.run("arktower.api:create_app", host=host, port=port, factory=True)
    else:
        console.print(f"[red]Unknown mode: {mode}. Use 'dashboard' or 'api'.[/red]")
        raise typer.Exit(1)


@app.command("migrate")
def server_migrate() -> None:
    """Run database migrations."""
    from arktower.store.connection import DatabaseConnection
    from arktower.store.migration import MigrationRunner

    from arktower.config import Settings

    settings = Settings()
    db = DatabaseConnection(settings.db_path)
    db.connect()
    migrations_dir = Path(__file__).resolve().parent.parent.parent / "migrations"
    runner = MigrationRunner(db, migrations_dir)
    applied = runner.run_migrations()
    if applied:
        console.print(f"[green]Applied {applied} migration(s).[/green]")
    else:
        console.print("[dim]Database is up to date.[/dim]")
    db.close()


@app.command("mcp")
def server_mcp() -> None:
    """Start the MCP server (stdio transport for Cursor/Claude integration)."""
    console.print("[bold green]Starting ArkTower MCP server (stdio)...[/bold green]")
    from arktower.mcp.server import main
    main()
