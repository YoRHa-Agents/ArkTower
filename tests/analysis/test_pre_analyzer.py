"""Tests for PreAnalyzer orchestration."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from arktower.analysis.complexity_scorer import (
    ComplexityLevel,
    ComplexityResult,
    ComplexityScorer,
)
from arktower.analysis.pre_analyzer import AnalysisResult, PreAnalyzer
from arktower.analysis.tag_extractor import TagExtractor


def test_analyze_returns_complexity_and_tags() -> None:
    pa = PreAnalyzer()
    r = pa.analyze(
        "Add FastAPI endpoint",
        "Implement REST API in Python with JWT auth",
        [],
    )
    assert isinstance(r, AnalysisResult)
    assert isinstance(r.complexity, ComplexityResult)
    assert r.complexity.level in ComplexityLevel
    assert "python" in r.suggested_tags
    assert "api" in r.suggested_tags
    assert "auth" in r.suggested_tags
    assert "fastapi" in r.suggested_tags


def test_suggested_tags_order_stable() -> None:
    pa = PreAnalyzer()
    r = pa.analyze("Py + React", "Use python and react", [])
    assert r.suggested_tags.index("python") < r.suggested_tags.index("react")


def test_analyze_passes_tags_to_scorer() -> None:
    pa = PreAnalyzer()
    with_tags = pa.analyze("t", "desc", ["x", "y", "z", "w", "v"])
    no_tags = pa.analyze("t", "desc", [])
    assert with_tags.complexity.score >= no_tags.complexity.score


def test_injected_scorer_used() -> None:
    mock = MagicMock(spec=ComplexityScorer)
    mock.score.return_value = ComplexityResult(
        level=ComplexityLevel.LOW,
        score=0.1,
        factors=["mock"],
    )
    pa = PreAnalyzer(scorer=mock)
    r = pa.analyze("a", "b", [])
    mock.score.assert_called_once_with("a", "b", [])
    assert r.complexity.score == 0.1


def test_injected_extractor_used() -> None:
    ex = MagicMock(spec=TagExtractor)
    ex.extract.return_value = ["custom"]
    pa = PreAnalyzer(extractor=ex)
    r = pa.analyze("x", "y", [])
    ex.extract.assert_called_once_with("x", "y")
    assert r.suggested_tags == ["custom"]


def test_javascript_and_typescript_tags() -> None:
    pa = PreAnalyzer()
    r = pa.analyze("Frontend", "Migrate from JS to TypeScript", [])
    assert "javascript" in r.suggested_tags
    assert "typescript" in r.suggested_tags


def test_docker_and_database_tags() -> None:
    pa = PreAnalyzer()
    r = pa.analyze(
        "DB",
        "Deploy with docker; use postgres for storage",
        [],
    )
    assert "docker" in r.suggested_tags
    assert "database" in r.suggested_tags


def test_go_golang_tag() -> None:
    pa = PreAnalyzer()
    r = pa.analyze("Svc", "Rewrite service in golang", [])
    assert "go" in r.suggested_tags


def test_analysis_result_model() -> None:
    pa = PreAnalyzer()
    r = pa.analyze("t", "d", [])
    dumped = r.model_dump()
    assert "complexity" in dumped and "suggested_tags" in dumped
