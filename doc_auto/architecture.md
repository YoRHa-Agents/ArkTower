# ArkTower Architecture Summary

> Last modified: 2026-04-14T18:00:00Z

_GitHub Pages (`docs/*.html`): code blocks use `<pre><code>` with copy buttons; styles in `docs/shared.css`. `docs/format.html` SPEC.004 task examples use tabbed `.task.md` / `.task.json` views (`.format-tabs` in `docs/shared.css`)._

## Overview

ArkTower is an agent-oriented task pool system built with Python 3.11+. It formats, normalizes, and pre-analyzes tasks for AI agent dispatch without executing them.

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Language | Python 3.11+ | Primary implementation |
| Database | SQLite (WAL mode) | Local-first task storage |
| API | FastAPI | REST + WebSocket endpoints |
| Dashboard | NiceGUI | Real-time web visualization |
| CLI | Typer + Rich | Terminal interface |
| AI Integration | MCP SDK | Cursor/Claude tool integration (12 tools) |
| Validation | Pydantic v2 | Data models and schema validation |
| Evaluation | Custom + NineS | 8-dimension self-benchmarking |

## Module Map

- `arktower/core/` — Domain models (`Task` with agent capabilities, `TaskStatus`, `Trigger`), state machine (15 triggers, 10 states), event bus, task service facade, task normalizer
- `arktower/store/` — `TaskRepository` Protocol, `SqliteTaskRepository` (CRUD, FTS5, atomic claim), migration runner (3 migrations)
- `arktower/api/` — FastAPI app factory, REST routes (`/api/v1/*` + `/api/v1/health`), WebSocket manager
- `arktower/mcp/` — MCP server with 12 tools, 1 resource, 2 prompts. Stdio transport for Cursor
- `arktower/cli/` — Typer CLI: `task`, `pool`, `server`, `eval` subcommands
- `arktower/web/` — NiceGUI dashboard with YoRHa Tower theme: i18n.py (EN/ZH translations, `t()` helper, `app.storage.user` language persistence), theme.py (dual dark/light design tokens and CSS, `get_colors()`/`get_theme_mode()` dynamic getters, `app.storage.user` theme persistence), dashboard.py (layout, header language + theme toggle buttons, scanline overlay), components/ (status badges, task cards — all using dynamic color getters), pages/ (pool overview, task board, task detail, analytics, dependency graph — all i18n-ized)
- `arktower/analysis/` — Pre-analysis pipeline: complexity scorer (heuristic), tag extractor (keyword-based)
- `arktower/archive/` — Snapshot writer (JSON), export formats (JSON/NDJSON/CSV/Markdown), archive service
- `arktower/evaluation/` — Self-benchmarking: 8 dimensions, gap detection, EvalRunner, golden tasks

## Task Lifecycle States

`submitted → queued → in_progress → [review | input_required | blocked] → completed | failed | canceled | timed_out`

All transitions are validated by the `StateMachine` class and recorded as `TaskEvent` audit entries.

## Agent Capability Matching

Tasks include `capabilities`, `required_tools`, and `estimated_complexity` fields. `TaskService.get_next_task_for_agent(capabilities)` matches queued tasks to agent capabilities.

## Self-Evaluation System

8 evaluation dimensions with weighted scoring:

| Dimension | Weight | Current Score |
|-----------|--------|--------------|
| lifecycle_correctness | 0.20 | 1.00 |
| task_format_quality | 0.15 | 0.87 |
| dispatch_reliability | 0.20 | 0.71 |
| search_effectiveness | 0.10 | 1.00 |
| api_completeness | 0.10 | 0.95 |
| analysis_accuracy | 0.10 | 1.00 |
| archive_integrity | 0.10 | 1.00 |
| concurrency_safety | 0.05 | 1.00 |

**Overall: 0.9179** (above standard gate ≥0.85)

## Test Coverage

293 tests, 71%+ overall coverage. Core modules at 96-100%.

## Integration

- `.cursor/mcp.json` — MCP server registration for Cursor
- `nines.toml` — NineS evaluation configuration
- `.workflow/config.yaml` — DevolaFlow self-update hooks and quality gates
- `docs/index.html` — GitHub Pages landing page (NieR:Automata Tower / YoRHa aesthetic)
- `docs/shared.css` — Shared design system (CSS variables, components, responsive utilities)
- `docs/format.html` — Task format specification page (YAML+MD format, field reference, state machine, dual-format task examples with tabs)
- `docs/demo.html` — Interactive client-side demo (task pool simulation, lifecycle controls, pre-analysis)
- `docs/docs.html` — Documentation hub (architecture, API reference, CLI, evaluation, configuration)

> Last modified: 2026-04-14T06:20:00Z (docs pages added)
