"""Tests for the ArkTower evaluation framework."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from arktower.evaluation.dimensions import (
    DIMENSION_WEIGHTS,
    DimensionScore,
    EvalDimension,
    EvalFinding,
    EvalReport,
)
from arktower.evaluation.evaluators import (
    AnalysisEvaluator,
    ApiCompletenessEvaluator,
    ArchiveEvaluator,
    ConcurrencyEvaluator,
    DispatchEvaluator,
    EvalContext,
    LifecycleEvaluator,
    SearchEvaluator,
    TaskFormatEvaluator,
)
from arktower.evaluation.golden_tasks import GOLDEN_TASKS
from arktower.evaluation.runner import EvalRunner


@pytest.fixture()
def ctx():
    return EvalContext()


class TestDimensionModels:
    def test_eval_dimension_enum_count(self):
        assert len(EvalDimension) == 8

    def test_weights_sum_to_one(self):
        total = sum(DIMENSION_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01

    def test_eval_finding_model(self):
        f = EvalFinding(
            severity="major",
            dimension=EvalDimension.LIFECYCLE_CORRECTNESS,
            title="Test finding",
            description="A test",
        )
        assert f.severity == "major"

    def test_dimension_score_model(self):
        ds = DimensionScore(
            dimension=EvalDimension.LIFECYCLE_CORRECTNESS,
            score=0.95,
            passed=19,
            failed=1,
        )
        assert ds.score == 0.95

    def test_eval_report_compute_overall(self):
        report = EvalReport(dimensions=[
            DimensionScore(dimension=d, score=0.9)
            for d in EvalDimension
        ])
        score = report.compute_overall()
        assert 0.85 <= score <= 0.95


class TestLifecycleEvaluator:
    def test_lifecycle_evaluator(self, ctx):
        ev = LifecycleEvaluator()
        result = ev.evaluate(ctx)
        assert result.dimension == EvalDimension.LIFECYCLE_CORRECTNESS
        assert result.score > 0.0
        assert result.passed > 0

    def test_lifecycle_covers_transitions(self, ctx):
        ev = LifecycleEvaluator()
        result = ev.evaluate(ctx)
        assert result.passed >= 10


class TestTaskFormatEvaluator:
    def test_format_evaluator(self, ctx):
        ev = TaskFormatEvaluator()
        result = ev.evaluate(ctx)
        assert result.dimension == EvalDimension.TASK_FORMAT_QUALITY
        assert result.score >= 0.8
        assert result.passed >= 6


class TestDispatchEvaluator:
    def test_dispatch_evaluator(self, ctx):
        ev = DispatchEvaluator()
        result = ev.evaluate(ctx)
        assert result.dimension == EvalDimension.DISPATCH_RELIABILITY
        assert result.score > 0.0
        assert result.passed >= 2


class TestSearchEvaluator:
    def test_search_evaluator(self, ctx):
        ev = SearchEvaluator()
        result = ev.evaluate(ctx)
        assert result.dimension == EvalDimension.SEARCH_EFFECTIVENESS
        assert result.passed >= 1


class TestApiCompletenessEvaluator:
    def test_api_completeness(self, ctx):
        ev = ApiCompletenessEvaluator()
        result = ev.evaluate(ctx)
        assert result.dimension == EvalDimension.API_COMPLETENESS
        assert result.score > 0.5
        assert result.passed >= 5


class TestAnalysisEvaluator:
    def test_analysis_evaluator(self, ctx):
        ev = AnalysisEvaluator()
        result = ev.evaluate(ctx)
        assert result.dimension == EvalDimension.ANALYSIS_ACCURACY
        assert result.passed >= 2


class TestArchiveEvaluator:
    def test_archive_evaluator(self, ctx):
        ev = ArchiveEvaluator()
        result = ev.evaluate(ctx)
        assert result.dimension == EvalDimension.ARCHIVE_INTEGRITY
        assert result.score >= 0.5


class TestConcurrencyEvaluator:
    def test_concurrency_evaluator(self, ctx):
        ev = ConcurrencyEvaluator()
        result = ev.evaluate(ctx)
        assert result.dimension == EvalDimension.CONCURRENCY_SAFETY
        assert result.score > 0.0


class TestEvalRunner:
    def test_full_run(self, ctx):
        runner = EvalRunner()
        report = runner.run(ctx)
        assert len(report.dimensions) == 8
        assert report.overall_score > 0.0
        assert len(report.recommendations) > 0

    def test_run_single_dimension(self, ctx):
        runner = EvalRunner()
        score = runner.run_dimension(EvalDimension.TASK_FORMAT_QUALITY, ctx)
        assert score.dimension == EvalDimension.TASK_FORMAT_QUALITY

    def test_report_json_serializable(self, ctx):
        runner = EvalRunner()
        report = runner.run(ctx)
        data = json.loads(json.dumps(report.model_dump(mode="json"), default=str))
        assert "overall_score" in data


class TestGoldenTasks:
    def test_golden_tasks_count(self):
        assert len(GOLDEN_TASKS) >= 10

    def test_golden_tasks_valid(self):
        from arktower.core.models import TaskCreate
        for gt in GOLDEN_TASKS:
            fields = {k: v for k, v in gt.items() if k in TaskCreate.model_fields}
            TaskCreate(**fields)
