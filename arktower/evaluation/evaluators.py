"""Concrete evaluators for each ArkTower capability dimension."""

from __future__ import annotations

import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from arktower.core.event_bus import EventBus
from arktower.core.models import (
    Task,
    TaskCreate,
    TaskFilter,
    TaskPriority,
    TaskStatus,
    TaskTemplate,
    TaskUpdate,
    Trigger,
)
from arktower.core.state_machine import TERMINAL_STATES, TRANSITION_TABLE, InvalidTransition, StateMachine
from arktower.core.task_service import TaskNotFoundError, TaskService
from arktower.evaluation.dimensions import DimensionScore, EvalDimension, EvalFinding
from arktower.store.connection import DatabaseConnection
from arktower.store.migration import MigrationRunner
from arktower.store.sqlite_repository import SqliteTaskRepository

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


class EvalContext(BaseModel):
    project_root: Path = Path(".")
    src_dir: Path = Path("arktower")
    test_dir: Path = Path("tests")
    db_path: str = ":memory:"

    model_config = {"arbitrary_types_allowed": True}


def _boot(ctx: EvalContext) -> tuple[DatabaseConnection, SqliteTaskRepository, TaskService]:
    db = DatabaseConnection(ctx.db_path)
    db.connect()
    if MIGRATIONS_DIR.is_dir():
        MigrationRunner(db, MIGRATIONS_DIR).run_migrations()
    repo = SqliteTaskRepository(db)
    bus = EventBus()
    svc = TaskService(repo, bus)
    return db, repo, svc


class BaseEvaluator(ABC):
    dimension: EvalDimension

    @abstractmethod
    def evaluate(self, ctx: EvalContext) -> DimensionScore:
        ...


class LifecycleEvaluator(BaseEvaluator):
    dimension = EvalDimension.LIFECYCLE_CORRECTNESS

    def evaluate(self, ctx: EvalContext) -> DimensionScore:
        sm = StateMachine()
        passed, failed, details, findings = 0, 0, [], []

        for trigger, transitions in TRANSITION_TABLE.items():
            for from_status, to_status in transitions.items():
                try:
                    result = sm.validate_transition(from_status, trigger)
                    if result == to_status:
                        passed += 1
                        details.append(f"PASS: {from_status} --{trigger}--> {to_status}")
                    else:
                        failed += 1
                        details.append(f"FAIL: {from_status} --{trigger}--> expected {to_status}, got {result}")
                except Exception as e:
                    failed += 1
                    details.append(f"ERROR: {from_status} --{trigger}--> {e}")

        for ts in TERMINAL_STATES:
            non_reopen = [t for t in Trigger if t != Trigger.REOPEN]
            for trigger in non_reopen:
                try:
                    sm.validate_transition(ts, trigger)
                    if trigger not in (Trigger.CANCEL,):
                        failed += 1
                        findings.append(EvalFinding(
                            severity="major",
                            dimension=self.dimension,
                            title=f"Terminal state {ts.value} accepts {trigger.value}",
                            description=f"Terminal state should reject non-reopen triggers",
                        ))
                except InvalidTransition:
                    passed += 1

        total = passed + failed
        score = passed / total if total > 0 else 0.0
        return DimensionScore(
            dimension=self.dimension, score=round(score, 4),
            passed=passed, failed=failed, details=details[:20], findings=findings,
        )


class TaskFormatEvaluator(BaseEvaluator):
    dimension = EvalDimension.TASK_FORMAT_QUALITY

    def evaluate(self, ctx: EvalContext) -> DimensionScore:
        passed, failed, details, findings = 0, 0, [], []

        required_fields = {"id", "title", "status", "priority", "created_at", "updated_at"}
        task_fields = set(Task.model_fields.keys())
        for f in required_fields:
            if f in task_fields:
                passed += 1
                details.append(f"PASS: required field '{f}' present")
            else:
                failed += 1
                findings.append(EvalFinding(
                    severity="blocker", dimension=self.dimension,
                    title=f"Missing required field: {f}",
                    description=f"Task model missing field '{f}'",
                ))

        try:
            t = Task(title="Test task")
            assert t.id
            assert t.status == TaskStatus.SUBMITTED
            assert t.priority == TaskPriority.MEDIUM
            passed += 1
            details.append("PASS: Task defaults correctly applied")
        except Exception as e:
            failed += 1
            details.append(f"FAIL: Task defaults: {e}")

        try:
            t = Task(title="Roundtrip test", description="Desc", tags=["py", "api"], priority=TaskPriority.HIGH)
            dumped = t.model_dump(mode="json")
            restored = Task.model_validate(dumped)
            assert restored.title == t.title
            assert restored.tags == t.tags
            assert restored.priority == t.priority
            passed += 1
            details.append("PASS: JSON roundtrip preserves data")
        except Exception as e:
            failed += 1
            details.append(f"FAIL: JSON roundtrip: {e}")

        try:
            t = Task(title="Unicode 测试 🏰", description="任务描述", tags=["中文"])
            assert "测试" in t.title
            passed += 1
            details.append("PASS: Unicode handling")
        except Exception as e:
            failed += 1
            details.append(f"FAIL: Unicode: {e}")

        # GAP: Agent capability matching fields
        agent_fields = {"capabilities", "required_tools", "estimated_complexity"}
        for af in agent_fields:
            if af in task_fields:
                passed += 1
                details.append(f"PASS: agent field '{af}' in Task model")
            else:
                failed += 1
                findings.append(EvalFinding(
                    severity="major", dimension=self.dimension,
                    title=f"Missing agent field: {af}",
                    description=f"Task model needs '{af}' for agent capability matching (designed in spec but not in model)",
                    suggestion=f"Add '{af}' field to Task model for agent-oriented dispatch",
                ))

        # GAP: .task.md file format parser
        try:
            from arktower.core import task_parser  # noqa: F401
            passed += 1
            details.append("PASS: .task.md parser module exists")
        except ImportError:
            failed += 1
            findings.append(EvalFinding(
                severity="major", dimension=self.dimension,
                title="No .task.md file format parser",
                description="Design spec defines a YAML frontmatter + Markdown body format but no parser exists",
                suggestion="Implement arktower.core.task_parser with parse_task_md() and serialize_task_md()",
            ))

        # GAP: JSON Schema validation
        try:
            from arktower.core import schema_validator  # noqa: F401
            passed += 1
            details.append("PASS: JSON Schema validator module exists")
        except ImportError:
            failed += 1
            findings.append(EvalFinding(
                severity="minor", dimension=self.dimension,
                title="No JSON Schema validator",
                description="Design spec includes a JSON Schema for task validation but no validator module",
                suggestion="Implement arktower.core.schema_validator using jsonschema library",
            ))

        # GAP: Task normalization pipeline
        try:
            from arktower.core import normalizer  # noqa: F401
            passed += 1
            details.append("PASS: Task normalizer module exists")
        except ImportError:
            failed += 1
            findings.append(EvalFinding(
                severity="major", dimension=self.dimension,
                title="No task normalization pipeline",
                description="Core feature: raw text → structured task conversion is not implemented",
                suggestion="Implement arktower.core.normalizer with normalize_raw_input(text) → TaskCreate",
            ))

        total = passed + failed
        return DimensionScore(
            dimension=self.dimension, score=round(passed / total, 4) if total > 0 else 0.0,
            passed=passed, failed=failed, details=details, findings=findings,
        )


class DispatchEvaluator(BaseEvaluator):
    dimension = EvalDimension.DISPATCH_RELIABILITY

    def evaluate(self, ctx: EvalContext) -> DimensionScore:
        import asyncio
        db, repo, svc = _boot(ctx)
        passed, failed, details, findings = 0, 0, [], []

        try:
            async def _full_lifecycle():
                task = await svc.create_task(TaskCreate(title="Dispatch test"))
                assert task.status == TaskStatus.SUBMITTED
                task = await svc.advance_task(task.id, Trigger.ENQUEUE)
                assert task.status == TaskStatus.QUEUED
                task = await svc.claim_task(task.id, "agent-1")
                assert task.status == TaskStatus.IN_PROGRESS
                assert task.assigned_to == "agent-1"
                task = await svc.complete_task(task.id, actor="agent-1", output="done")
                assert task.status == TaskStatus.COMPLETED
                return task

            asyncio.run(_full_lifecycle())
            passed += 1
            details.append("PASS: Full lifecycle create→enqueue→claim→complete")
        except Exception as e:
            failed += 1
            details.append(f"FAIL: Full lifecycle: {e}")

        try:
            async def _double_claim():
                task = await svc.create_task(TaskCreate(title="Double claim test"))
                await svc.advance_task(task.id, Trigger.ENQUEUE)
                await svc.claim_task(task.id, "agent-1")
                try:
                    await svc.claim_task(task.id, "agent-2")
                    return False
                except (InvalidTransition, Exception):
                    return True

            result = asyncio.run(_double_claim())
            if result:
                passed += 1
                details.append("PASS: Double claim correctly rejected")
            else:
                failed += 1
                findings.append(EvalFinding(
                    severity="blocker", dimension=self.dimension,
                    title="Double claim not prevented",
                    description="Second claim on an in-progress task should be rejected",
                ))
        except Exception as e:
            failed += 1
            details.append(f"FAIL: Double claim test: {e}")

        try:
            async def _fail_flow():
                task = await svc.create_task(TaskCreate(title="Fail test"))
                await svc.advance_task(task.id, Trigger.ENQUEUE)
                await svc.claim_task(task.id, "agent-1")
                task = await svc.fail_task(task.id, actor="agent-1", error="test error")
                assert task.status == TaskStatus.FAILED
                assert task.error == "test error"

            asyncio.run(_fail_flow())
            passed += 1
            details.append("PASS: Fail flow sets error correctly")
        except Exception as e:
            failed += 1
            details.append(f"FAIL: Fail flow: {e}")

        try:
            events = repo.get_history(repo.list(TaskFilter(limit=1))[0].id)
            if len(events) >= 1:
                passed += 1
                details.append(f"PASS: Event audit trail ({len(events)} events)")
            else:
                failed += 1
                details.append("FAIL: No events recorded")
        except Exception as e:
            failed += 1
            details.append(f"FAIL: Event audit: {e}")

        # GAP: Agent capability matching in dispatch
        if hasattr(svc, "get_next_task_for_agent"):
            passed += 1
            details.append("PASS: Capability-based agent matching exists")
        else:
            failed += 1
            findings.append(EvalFinding(
                severity="major", dimension=self.dimension,
                title="No capability-based task matching",
                description="get_next_task() doesn't match agent capabilities to task requirements",
                suggestion="Add get_next_task_for_agent(agent_capabilities) method to TaskService",
            ))

        # GAP: Task dependency enforcement on dispatch
        try:
            async def _dep_check():
                t1 = await svc.create_task(TaskCreate(title="Dep parent"))
                t2 = await svc.create_task(TaskCreate(title="Dep child"))
                from arktower.core.models import Dependency, DependencyType
                repo.create_dependency(Dependency(from_task_id=t2.id, to_task_id=t1.id))
                await svc.advance_task(t2.id, Trigger.ENQUEUE)
                await svc.advance_task(t1.id, Trigger.ENQUEUE)
                # child should ideally be blocked until parent completes
                child = svc.get_task(t2.id)
                return child.status == TaskStatus.BLOCKED

            blocks = asyncio.run(_dep_check())
            if blocks:
                passed += 1
                details.append("PASS: Dependency enforcement blocks child task")
            else:
                failed += 1
                findings.append(EvalFinding(
                    severity="major", dimension=self.dimension,
                    title="No dependency enforcement on enqueue",
                    description="Tasks with unresolved dependencies can be enqueued without blocking",
                    suggestion="Add dependency gate check in advance_task for ENQUEUE trigger",
                ))
        except Exception:
            failed += 1
            findings.append(EvalFinding(
                severity="major", dimension=self.dimension,
                title="No dependency enforcement on enqueue",
                description="Tasks with unresolved dependencies can be enqueued without blocking",
                suggestion="Add dependency gate check in advance_task for ENQUEUE trigger",
            ))

        # GAP: Batch operations
        if hasattr(svc, "create_tasks_batch"):
            passed += 1
            details.append("PASS: Batch task creation exists")
        else:
            failed += 1
            findings.append(EvalFinding(
                severity="minor", dimension=self.dimension,
                title="No batch task operations",
                description="No create_tasks_batch() for bulk ingestion",
                suggestion="Add batch create/update methods for high-throughput task ingestion",
            ))

        db.close()
        total = passed + failed
        return DimensionScore(
            dimension=self.dimension, score=round(passed / total, 4) if total > 0 else 0.0,
            passed=passed, failed=failed, details=details, findings=findings,
        )


class SearchEvaluator(BaseEvaluator):
    dimension = EvalDimension.SEARCH_EFFECTIVENESS

    def evaluate(self, ctx: EvalContext) -> DimensionScore:
        import asyncio
        db, repo, svc = _boot(ctx)
        passed, failed, details, findings = 0, 0, [], []

        async def _setup():
            await svc.create_task(TaskCreate(title="JWT authentication module", tags=["auth", "python"]))
            await svc.create_task(TaskCreate(title="Database migration script", tags=["database", "sql"]))
            await svc.create_task(TaskCreate(title="React frontend dashboard", tags=["frontend", "react"]))

        asyncio.run(_setup())

        for query, expected_min in [("JWT", 1), ("authentication", 1), ("database", 1), ("React", 1)]:
            results = svc.list_tasks(TaskFilter(search=query))
            if len(results) >= expected_min:
                passed += 1
                details.append(f"PASS: FTS '{query}' returned {len(results)} (expected >={expected_min})")
            else:
                failed += 1
                details.append(f"FAIL: FTS '{query}' returned {len(results)} (expected >={expected_min})")
                findings.append(EvalFinding(
                    severity="major", dimension=self.dimension,
                    title=f"FTS miss for '{query}'",
                    description=f"Expected >={expected_min} results, got {len(results)}",
                ))

        results = svc.list_tasks(TaskFilter(tags=["auth"]))
        if any("auth" in t.tags for t in results):
            passed += 1
            details.append("PASS: Tag filter for 'auth'")
        else:
            failed += 1
            details.append("FAIL: Tag filter for 'auth'")

        results = svc.list_tasks(TaskFilter(status=[TaskStatus.SUBMITTED]))
        if len(results) >= 3:
            passed += 1
            details.append("PASS: Status filter")
        else:
            failed += 1
            details.append(f"FAIL: Status filter returned {len(results)}")

        db.close()
        total = passed + failed
        return DimensionScore(
            dimension=self.dimension, score=round(passed / total, 4) if total > 0 else 0.0,
            passed=passed, failed=failed, details=details, findings=findings,
        )


class ApiCompletenessEvaluator(BaseEvaluator):
    dimension = EvalDimension.API_COMPLETENESS

    def evaluate(self, ctx: EvalContext) -> DimensionScore:
        passed, failed, details, findings = 0, 0, [], []

        try:
            from arktower.api.rest_routes import router
            routes = [r.path for r in router.routes if hasattr(r, "path")]
            expected = ["/tasks", "/tasks/{task_id}", "/pool/stats", "/pool/next",
                        "/templates", "/archives/{task_id}"]
            for ep in expected:
                if any(ep in r for r in routes):
                    passed += 1
                    details.append(f"PASS: endpoint {ep}")
                else:
                    failed += 1
                    findings.append(EvalFinding(
                        severity="major", dimension=self.dimension,
                        title=f"Missing endpoint: {ep}",
                        description=f"Expected REST endpoint {ep} not found",
                    ))
        except Exception as e:
            failed += 1
            details.append(f"FAIL: Route inspection: {e}")

        try:
            from arktower.mcp.server import TOOL_DEFINITIONS
            tool_names = {td["name"] for td in TOOL_DEFINITIONS}
            expected_tools = {"create_task", "list_tasks", "get_task", "claim_task",
                             "complete_task", "search_tasks", "get_pool_stats", "get_next_task"}
            for t in expected_tools:
                if t in tool_names:
                    passed += 1
                    details.append(f"PASS: MCP tool '{t}'")
                else:
                    failed += 1
                    findings.append(EvalFinding(
                        severity="major", dimension=self.dimension,
                        title=f"Missing MCP tool: {t}",
                        description=f"Expected MCP tool '{t}' not registered",
                    ))
        except Exception as e:
            failed += 1
            details.append(f"FAIL: MCP tool inspection: {e}")

        # GAP: MCP advance/fail tools
        desired_extra_tools = {"advance_task", "fail_task", "archive_task", "create_from_template"}
        try:
            from arktower.mcp.server import TOOL_DEFINITIONS as td
            tool_names_full = {t["name"] for t in td}
            for dt in desired_extra_tools:
                if dt in tool_names_full:
                    passed += 1
                    details.append(f"PASS: MCP tool '{dt}'")
                else:
                    failed += 1
                    findings.append(EvalFinding(
                        severity="minor", dimension=self.dimension,
                        title=f"Missing MCP tool: {dt}",
                        description=f"Agent-useful MCP tool '{dt}' not yet implemented",
                        suggestion=f"Add {dt} to MCP tool definitions for richer agent interaction",
                    ))
        except Exception:
            for dt in desired_extra_tools:
                failed += 1

        # GAP: REST API authentication
        try:
            from arktower.api import rest_routes
            src = Path(rest_routes.__file__).read_text()
            if "Authorization" in src or "api_key" in src or "auth" in src.lower().split("def ")[0]:
                passed += 1
                details.append("PASS: API has authentication")
            else:
                failed += 1
                findings.append(EvalFinding(
                    severity="minor", dimension=self.dimension,
                    title="No API authentication",
                    description="REST endpoints have no auth mechanism",
                    suggestion="Add API key or token-based auth middleware",
                ))
        except Exception:
            failed += 1

        # GAP: Health check endpoint
        try:
            from arktower.api.rest_routes import router as api_router
            route_paths = [r.path for r in api_router.routes if hasattr(r, "path")]
            if any("health" in r for r in route_paths):
                passed += 1
                details.append("PASS: /health endpoint exists")
            else:
                failed += 1
                findings.append(EvalFinding(
                    severity="minor", dimension=self.dimension,
                    title="No health check endpoint",
                    description="No /health or /api/v1/health endpoint",
                    suggestion="Add GET /api/v1/health returning {status: 'ok', version: ...}",
                ))
        except Exception:
            failed += 1

        total = passed + failed
        return DimensionScore(
            dimension=self.dimension, score=round(passed / total, 4) if total > 0 else 0.0,
            passed=passed, failed=failed, details=details, findings=findings,
        )


class AnalysisEvaluator(BaseEvaluator):
    dimension = EvalDimension.ANALYSIS_ACCURACY

    def evaluate(self, ctx: EvalContext) -> DimensionScore:
        from arktower.analysis.complexity_scorer import ComplexityScorer
        from arktower.analysis.pre_analyzer import PreAnalyzer
        from arktower.analysis.tag_extractor import TagExtractor

        passed, failed, details, findings = 0, 0, [], []

        scorer = ComplexityScorer()
        for title, desc, expected_min, expected_max in [
            ("Fix typo", "", 0.0, 0.3),
            (
                "Refactor distributed authentication architecture",
                "Migrate the legacy authorization layer to support concurrent distributed "
                "session management. Handle race conditions in the session store and add "
                "encryption for backward compatibility.\n"
                "- [ ] Design new auth architecture\n"
                "- [ ] Implement distributed session store\n"
                "- [ ] Add encryption for session tokens\n"
                "- [ ] Migration script for legacy data\n"
                "- [ ] Performance optimization and scalability testing\n",
                0.3, 1.0,
            ),
        ]:
            result = scorer.score(title, desc, [])
            if expected_min <= result.score <= expected_max:
                passed += 1
                details.append(f"PASS: complexity '{title[:30]}' = {result.score:.2f} (in [{expected_min},{expected_max}])")
            else:
                failed += 1
                details.append(f"FAIL: complexity '{title[:30]}' = {result.score:.2f} (expected [{expected_min},{expected_max}])")

        extractor = TagExtractor()
        tags = extractor.extract("Implement FastAPI endpoint", "Use Python and PostgreSQL for the database")
        if "python" in tags or "fastapi" in tags:
            passed += 1
            details.append(f"PASS: Tag extraction found: {tags}")
        else:
            failed += 1
            details.append(f"FAIL: Tag extraction missed expected tags. Got: {tags}")

        analyzer = PreAnalyzer()
        result = analyzer.analyze("Build React dashboard", "Frontend with TypeScript and Tailwind CSS")
        if result.complexity and result.suggested_tags:
            passed += 1
            details.append("PASS: PreAnalyzer returns both complexity and tags")
        else:
            failed += 1
            details.append("FAIL: PreAnalyzer incomplete result")

        total = passed + failed
        return DimensionScore(
            dimension=self.dimension, score=round(passed / total, 4) if total > 0 else 0.0,
            passed=passed, failed=failed, details=details, findings=findings,
        )


class ArchiveEvaluator(BaseEvaluator):
    dimension = EvalDimension.ARCHIVE_INTEGRITY

    def evaluate(self, ctx: EvalContext) -> DimensionScore:
        import asyncio
        import tempfile
        from arktower.archive.snapshot_writer import SnapshotWriter
        from arktower.archive.export_formats import ExportFormats

        passed, failed, details, findings = 0, 0, [], []

        with tempfile.TemporaryDirectory() as tmp:
            db, repo, svc = _boot(ctx)

            async def _setup():
                t = await svc.create_task(TaskCreate(title="Archive test"))
                await svc.advance_task(t.id, Trigger.ENQUEUE)
                await svc.claim_task(t.id, "agent-1")
                await svc.complete_task(t.id, actor="agent-1", output="done")
                return t.id

            task_id = asyncio.run(_setup())
            task = repo.get(task_id)
            history = repo.get_history(task_id)

            writer = SnapshotWriter(Path(tmp))
            path = writer.write_snapshot(task, history)
            if path.exists():
                passed += 1
                details.append("PASS: Snapshot written to disk")
            else:
                failed += 1
                details.append("FAIL: Snapshot file not created")

            restored = writer.read_snapshot(task_id)
            if restored and restored["task"]["title"] == "Archive test":
                passed += 1
                details.append("PASS: Snapshot roundtrip preserves data")
            else:
                failed += 1
                details.append("FAIL: Snapshot roundtrip data mismatch")

            snapshots = writer.list_snapshots()
            if len(snapshots) == 1:
                passed += 1
                details.append("PASS: list_snapshots returns 1")
            else:
                failed += 1
                details.append(f"FAIL: list_snapshots returned {len(snapshots)}")

            db.close()

        total = passed + failed
        return DimensionScore(
            dimension=self.dimension, score=round(passed / total, 4) if total > 0 else 0.0,
            passed=passed, failed=failed, details=details, findings=findings,
        )


class ConcurrencyEvaluator(BaseEvaluator):
    dimension = EvalDimension.CONCURRENCY_SAFETY

    def evaluate(self, ctx: EvalContext) -> DimensionScore:
        passed, failed, details, findings = 0, 0, [], []

        db = DatabaseConnection(":memory:")
        db.connect()
        conn = db.get_connection()

        row = conn.execute("PRAGMA foreign_keys").fetchone()
        if row and row[0] == 1:
            passed += 1
            details.append("PASS: foreign_keys enabled")
        else:
            failed += 1
            findings.append(EvalFinding(
                severity="critical", dimension=self.dimension,
                title="Foreign keys disabled",
                description="PRAGMA foreign_keys should be ON",
            ))

        row = conn.execute("PRAGMA busy_timeout").fetchone()
        if row and row[0] > 0:
            passed += 1
            details.append(f"PASS: busy_timeout = {row[0]}ms")
        else:
            failed += 1
            details.append("FAIL: busy_timeout not set")

        if MIGRATIONS_DIR.is_dir():
            MigrationRunner(db, MIGRATIONS_DIR).run_migrations()
        repo = SqliteTaskRepository(db)

        task = Task(title="Concurrency test", status=TaskStatus.QUEUED)
        repo.create(task)
        try:
            repo.atomic_claim(task.id, "agent-1")
            claimed = repo.get(task.id)
            if claimed and claimed.status == TaskStatus.IN_PROGRESS:
                passed += 1
                details.append("PASS: atomic_claim works")
            else:
                failed += 1
                details.append("FAIL: atomic_claim did not set IN_PROGRESS")
        except Exception as e:
            failed += 1
            details.append(f"FAIL: atomic_claim: {e}")

        db.close()
        total = passed + failed
        return DimensionScore(
            dimension=self.dimension, score=round(passed / total, 4) if total > 0 else 0.0,
            passed=passed, failed=failed, details=details, findings=findings,
        )


ALL_EVALUATORS: list[type[BaseEvaluator]] = [
    LifecycleEvaluator,
    TaskFormatEvaluator,
    DispatchEvaluator,
    SearchEvaluator,
    ApiCompletenessEvaluator,
    AnalysisEvaluator,
    ArchiveEvaluator,
    ConcurrencyEvaluator,
]
