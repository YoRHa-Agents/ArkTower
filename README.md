```
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║          ▄▀▀▀▄   ▄▀▀▀▄  ▄   ▄  ▄▀▀▀▀▀▀▄  ▄▀▀▀▄           ║
    ║         █     █  █     █ █  █   █  ▄▄▄▄▄▀  █     █          ║
    ║         █▀▀▀▀█   █▀▀▀▀▀ █▀▀    █  █▄▄▄▄   █▀▀▀▀▀          ║
    ║         █     █  █   █  █  █   █       █  █   █             ║
    ║         █     █  █    █ █   █  █▄▄▄▄▄▄▀  █    █            ║
    ║                                                              ║
    ║              ████████╗ ██████╗ ██╗    ██╗███████╗            ║
    ║              ╚══██╔══╝██╔═══██╗██║    ██║██╔════╝            ║
    ║                 ██║   ██║   ██║██║ █╗ ██║█████╗              ║
    ║                 ██║   ██║   ██║██║███╗██║██╔══╝              ║
    ║                 ██║   ╚██████╔╝╚███╔███╔╝███████╗            ║
    ║                 ╚═╝    ╚═════╝  ╚══╝╚══╝ ╚══════╝            ║
    ║                                                              ║
    ║               ▮  A R K T O W E R  ▮                          ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
```

---

> **[PROJECT CLASSIFICATION: PUBLIC]** &nbsp; **[SYSTEM: ArkTower]** &nbsp; **[VERSION: 0.1.0]**
>
> Agent-oriented task pool system — format, normalize, pre-analyze, and dispatch tasks for AI agents.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-DAD4BB?style=flat-square&labelColor=0D0D0D)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-DAD4BB?style=flat-square&labelColor=0D0D0D)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-293%20passed-8BAA7F?style=flat-square&labelColor=0D0D0D)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-71%25-DAD4BB?style=flat-square&labelColor=0D0D0D)](tests/)
[![NiceGUI](https://img.shields.io/badge/dashboard-NiceGUI-C7372F?style=flat-square&labelColor=0D0D0D)](https://nicegui.io)

---

## > SYSTEM.OVERVIEW

ArkTower provides a **universal task pool** where tasks are uniformly structured, pre-decomposed, and ready for agent dispatch or automatic claiming. It does not execute tasks itself — it serves as the **foundation for agent-driven workflows**.

```
[CAPABILITIES]
├── Universal Task Format    YAML frontmatter + Markdown body (.task.md)
├── 10-State Lifecycle       submitted → queued → in_progress → ... → completed
├── Named-Trigger Engine     Verbs (claim, complete, block) with gate checks
├── Pre-Analysis Pipeline    Automatic complexity scoring + tag extraction
├── Local-First Storage      SQLite WAL mode, FTS5 search, zero dependencies
├── REST API + WebSocket     Full CRUD, real-time events via FastAPI
├── MCP Integration          Native Cursor / Claude / MCP-compatible tools
├── CLI Interface            Rich terminal interface via Typer
├── Web Dashboard            Real-time NiceGUI dashboard — YoRHa Tower theme
└── Task Archival            Snapshot to JSON, export CSV/NDJSON/Markdown
```

---

## > QUICK.START

```bash
# [INSTALL] Clone and install
pip install -e ".[dev]"

# [MIGRATE] Initialize the database
arktower server migrate

# [DEPLOY] Start the dashboard (NiceGUI + API)
arktower server start

# [DEPLOY] API-only mode
arktower server start --mode api

# [DEPLOY] MCP server for Cursor integration
arktower server mcp
```

---

## > OPERATIONS.CLI

```bash
# [CREATE] New task entry
arktower task create "Implement JWT authentication" \
  --priority high \
  --tags "python,api,auth" \
  --description "Add JWT-based auth to the API gateway"

# [QUERY] List and filter tasks
arktower task list
arktower task list --status queued --json

# [ADVANCE] Task lifecycle transitions
arktower task advance <task-id> enqueue
arktower task claim <task-id> agent-1
arktower task complete <task-id> --output "Implemented in PR #42"

# [STATUS] Pool operations
arktower pool stats
arktower pool next
```

---

## > INTEGRATION.MCP

ArkTower registers as an MCP server for Cursor. Configuration in `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "arktower": {
      "command": "python",
      "args": ["-m", "arktower.mcp.server"]
    }
  }
}
```

```
[MCP TOOLS]
├── create_task       Create new task entry
├── list_tasks        Query with filters
├── get_task          Retrieve by ID
├── claim_task        Agent claims ownership
├── complete_task     Mark task complete
├── search_tasks      Full-text search
├── get_pool_stats    Pool metrics
└── get_next_task     Priority-based dispatch
```

---

## > ARCHITECTURE.DIAGRAM

```
╔════════════════════════════════════════════════════════════════════╗
║                     [EXTERNAL CONSUMERS]                          ║
║   Cursor (MCP)  │  OpenClaw  │  REST API  │  Dashboard  │  CLI   ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║   ┌────────────┐  ┌────────────┐  ┌─────────┐  ┌──────────────┐  ║
║   │ MCP Server │  │ REST API   │  │   CLI   │  │   NiceGUI    │  ║
║   │  (stdio)   │  │ (FastAPI)  │  │ (Typer) │  │  Dashboard   │  ║
║   └─────┬──────┘  └─────┬──────┘  └────┬────┘  └──────┬───────┘  ║
║         └───────────────┬┘──────────────┘──────────────┘          ║
║                         │                                          ║
║              ┌──────────▼──────────┐                               ║
║              │    Task Service     │◄──── EventBus (pub/sub)       ║
║              └──────────┬──────────┘                               ║
║              ┌──────────▼──────────┐                               ║
║              │   State Machine     │  15 triggers × 10 states      ║
║              └──────────┬──────────┘                               ║
║              ┌──────────▼──────────┐                               ║
║              │  SQLite (WAL mode)  │  FTS5 · JSON1 · Indexes      ║
║              └─────────────────────┘                               ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
```

---

## > PROJECT.STRUCTURE

```
arktower/
├── core/          # Domain models, state machine, event bus, task service
├── store/         # SQLite repository, connection, migrations
├── api/           # FastAPI REST + WebSocket endpoints
├── mcp/           # MCP server (tools, resources, prompts)
├── cli/           # Typer CLI commands
├── web/           # NiceGUI dashboard — YoRHa Tower theme
│   ├── theme.py        # Design tokens, colors, global CSS
│   ├── dashboard.py    # Layout, navigation, scanline overlay
│   ├── components/     # Status badges, task cards, priority indicators
│   └── pages/          # Pool overview, task board, detail, analytics, graph
├── analysis/      # Pre-analysis pipeline (complexity, tags)
└── archive/       # Task archival, snapshots, export formats
```

---

## > DEVELOPMENT.PROTOCOL

```bash
# [INSTALL] Dev dependencies
pip install -e ".[dev]"

# [TEST] Run test suite
python -m pytest tests/ -v

# [TEST] Coverage report
python -m pytest tests/ --cov=arktower --cov-report=term-missing

# [LINT] Static analysis
python -m ruff check arktower/
```

---

## > LICENSE

MIT — see [LICENSE](LICENSE).

---

<p align="center">
  <sub><em>Glory to Mankind. — YoRHa</em></sub>
</p>
