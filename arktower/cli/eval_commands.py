"""Evaluation subcommands for the ArkTower CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="eval", help="Self-evaluation and benchmarking commands.")
console = Console()


@app.command("run")
def eval_run(
    dimension: Optional[str] = typer.Option(None, "--dimension", "-d", help="Run specific dimension only"),
    output_dir: Optional[str] = typer.Option(None, "--output-dir", "-o", help="Save report to directory"),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Run the self-evaluation benchmark."""
    from arktower.evaluation.dimensions import EvalDimension
    from arktower.evaluation.evaluators import EvalContext
    from arktower.evaluation.runner import EvalRunner, run_and_save

    ctx = EvalContext()
    out_path = Path(output_dir) if output_dir else Path(".local/eval_reports")

    if dimension:
        dim = EvalDimension(dimension)
        runner = EvalRunner()
        score = runner.run_dimension(dim, ctx)
        if as_json:
            console.print(json.dumps(score.model_dump(mode="json"), indent=2, default=str))
        else:
            console.print(f"[bold]{dim.value}[/bold]: {score.score:.2f} ({score.passed}P/{score.failed}F)")
            for d in score.details:
                console.print(f"  {d}")
        return

    report = run_and_save(ctx, output_dir=out_path)

    if as_json:
        console.print(json.dumps(report.model_dump(mode="json"), indent=2, default=str))
        return

    table = Table(title="ArkTower Self-Evaluation", show_header=True, header_style="bold")
    table.add_column("Dimension", min_width=28)
    table.add_column("Score", justify="right")
    table.add_column("Pass/Fail", justify="right")
    table.add_column("Status")

    for ds in report.dimensions:
        score_str = f"{ds.score:.2f}"
        pf_str = f"{ds.passed}/{ds.failed}"
        status = "[green]PASS[/green]" if ds.score >= 0.8 else "[yellow]WARN[/yellow]" if ds.score >= 0.6 else "[red]FAIL[/red]"
        table.add_row(ds.dimension.value, score_str, pf_str, status)

    console.print(table)
    console.print(f"\n[bold]Overall Score: {report.overall_score:.4f}[/bold]")

    if report.findings:
        console.print(f"\n[bold]Findings ({len(report.findings)}):[/bold]")
        for f in report.findings[:10]:
            sev_color = {"blocker": "red", "critical": "red", "major": "yellow", "minor": "dim", "info": "dim"}.get(f.severity, "white")
            console.print(f"  [{sev_color}][{f.severity.upper()}][/{sev_color}] {f.title}")

    if report.recommendations:
        console.print("\n[bold]Recommendations:[/bold]")
        for r in report.recommendations:
            console.print(f"  • {r}")


@app.command("report")
def eval_report(
    report_dir: str = typer.Option(".local/eval_reports", help="Directory with eval reports"),
) -> None:
    """Show the latest evaluation report."""
    reports = sorted(Path(report_dir).glob("eval_report_*.json"), reverse=True)
    if not reports:
        console.print("[dim]No evaluation reports found.[/dim]")
        return

    latest = reports[0]
    data = json.loads(latest.read_text())
    console.print(f"[bold]Latest Report:[/bold] {latest.name}")
    console.print(f"  Overall Score: {data.get('overall_score', 'N/A')}")
    console.print(f"  Timestamp: {data.get('timestamp', 'N/A')}")
    dims = data.get("dimensions", [])
    for d in dims:
        console.print(f"  {d['dimension']}: {d['score']:.2f} ({d['passed']}P/{d['failed']}F)")


@app.command("golden")
def eval_golden() -> None:
    """Validate golden test tasks."""
    from arktower.core.models import Task, TaskCreate
    from arktower.evaluation.golden_tasks import GOLDEN_TASKS

    passed, failed = 0, 0
    for gt in GOLDEN_TASKS:
        try:
            TaskCreate(**{k: v for k, v in gt.items() if k in TaskCreate.model_fields})
            passed += 1
            console.print(f"  [green]PASS[/green] {gt['title'][:60]}")
        except Exception as e:
            failed += 1
            console.print(f"  [red]FAIL[/red] {gt['title'][:60]}: {e}")

    console.print(f"\nGolden tasks: {passed} passed, {failed} failed out of {len(GOLDEN_TASKS)}")
