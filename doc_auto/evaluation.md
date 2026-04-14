# ArkTower Self-Evaluation System

> Last modified: 2026-04-14T12:00:00Z

## Overview

ArkTower includes a built-in self-evaluation framework that benchmarks the system across 8 agent-oriented capability dimensions. The system drives self-improvement iteration cycles.

## Evaluation Dimensions

| Dimension | Weight | Description |
|-----------|--------|-------------|
| `lifecycle_correctness` | 20% | State machine transitions, terminal state enforcement, audit trail |
| `task_format_quality` | 15% | Task model completeness, agent fields, .task.md parser, normalizer |
| `dispatch_reliability` | 20% | Lifecycle flows, atomic claims, capability matching, dependency gates |
| `search_effectiveness` | 10% | FTS5 retrieval, tag filtering, combined filter accuracy |
| `api_completeness` | 10% | REST endpoints, MCP tools, health check, auth |
| `analysis_accuracy` | 10% | Complexity scoring calibration, tag extraction recall |
| `archive_integrity` | 10% | Snapshot roundtrip, export format correctness |
| `concurrency_safety` | 5% | SQLite pragmas, atomic operations, FK enforcement |

## Running Evaluations

```bash
# Full evaluation
arktower eval run

# Specific dimension
arktower eval run --dimension lifecycle_correctness

# JSON output
arktower eval run --json

# View latest report
arktower eval report

# Validate golden tasks
arktower eval golden

# Direct runner
python -m arktower.evaluation.runner
```

## Quality Gates (from .workflow/config.yaml)

| Gate | Composite Threshold | Coverage |
|------|-------------------|----------|
| Relaxed | ≥0.70 | ≥60% |
| Standard | ≥0.85 | ≥80% |
| Strict | ≥0.90 | ≥90% |

## Iteration History

| Round | Date | Overall | Key Changes |
|-------|------|---------|-------------|
| Baseline (gap-unaware) | 2026-04-14 | 1.0000 | Initial evaluators (correctness-only checks) |
| Baseline (gap-detecting) | 2026-04-14 | 0.8243 | Added gap detection for missing features |
| Iteration 1 | 2026-04-14 | 0.9179 | +agent capability fields, +normalizer, +4 MCP tools, +health endpoint, +capability matching |

## Remaining Findings (after Iteration 1)

| Severity | Finding | Dimension |
|----------|---------|-----------|
| MAJOR | No .task.md file format parser | task_format_quality |
| MAJOR | No dependency enforcement on enqueue | dispatch_reliability |
| MINOR | No JSON Schema validator | task_format_quality |
| MINOR | No batch task operations | dispatch_reliability |
| MINOR | No API authentication | api_completeness |

## NineS Integration

Configuration in `nines.toml`. The evaluation framework aligns with NineS capability dimensions for `nines self-eval` and `nines iterate` commands.

## Architecture

Package layout under `arktower/evaluation/`:

- `__init__.py` — Public API exports
- `dimensions.py` — `EvalDimension` enum, `DimensionScore`, `EvalReport` models
- `evaluators.py` — Eight concrete evaluators with gap-detection checks
- `golden_tasks.py` — Twelve golden test tasks for format validation
- `runner.py` — `EvalRunner` orchestrator and `__main__` entry point
