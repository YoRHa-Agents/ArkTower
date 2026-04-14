"""Tests for ComplexityScorer."""

from __future__ import annotations

import pytest

from arktower.analysis.complexity_scorer import (
    ComplexityLevel,
    ComplexityResult,
    ComplexityScorer,
)


@pytest.fixture
def scorer() -> ComplexityScorer:
    return ComplexityScorer()


def test_trivial_short_task(scorer: ComplexityScorer) -> None:
    r = scorer.score("x", "ok", [])
    assert r.level == ComplexityLevel.TRIVIAL
    assert r.score < 0.25
    assert len(r.factors) == 4


def test_long_description_raises_level(scorer: ComplexityScorer) -> None:
    body = "word " * 500
    r = scorer.score("Title", body, [])
    assert r.score >= 0.5
    assert r.level in (
        ComplexityLevel.MEDIUM,
        ComplexityLevel.HIGH,
        ComplexityLevel.EXTREME,
    )


def test_checkboxes_increase_score(scorer: ComplexityScorer) -> None:
    base = scorer.score("t", "hello world", [])
    with_boxes = scorer.score(
        "t",
        "hello\n- [ ]\n- [ ]\n- [ ]\n- [ ]\n- [ ]\n",
        [],
    )
    assert with_boxes.score > base.score
    assert "checklist" in " ".join(with_boxes.factors).lower()


def test_keyword_hits_increase_density(scorer: ComplexityScorer) -> None:
    plain = scorer.score("task", "do something simple today", [])
    dense = scorer.score(
        "task",
        "migration architecture integration security refactor distributed system",
        [],
    )
    assert dense.score > plain.score
    assert any("keyword" in f.lower() for f in dense.factors)


def test_many_tags_bump_score(scorer: ComplexityScorer) -> None:
    few = scorer.score("t", "desc", ["a", "b"])
    many = scorer.score("t", "desc", list("abcdefghij"))
    assert many.score >= few.score


def test_result_is_pydantic_complexity_result(scorer: ComplexityScorer) -> None:
    r = scorer.score("a", "b", [])
    assert isinstance(r, ComplexityResult)
    assert 0.0 <= r.score <= 1.0


def test_extreme_checklist_and_length(scorer: ComplexityScorer) -> None:
    lines = "\n".join(f"- [ ] step {i}" for i in range(25))
    long_intro = "context " * 300
    r = scorer.score("Big", f"{long_intro}\n{lines}", [])
    assert r.level in (ComplexityLevel.HIGH, ComplexityLevel.EXTREME)
    assert r.score >= 0.65


def test_ordered_checkbox_markers(scorer: ComplexityScorer) -> None:
    md = "1. [ ] first\n2. [x] done\n* [ ] third"
    r = scorer.score("t", md, [])
    assert r.score > 0.05
    assert any("checklist" in f.lower() for f in r.factors)


def test_level_low_band(scorer: ComplexityScorer) -> None:
    # Tuned: medium length, no boxes, almost no keywords → expect low/medium.
    text = "implement small fix " + ("details " * 40)
    r = scorer.score("Fix", text, [])
    assert r.level in (
        ComplexityLevel.LOW,
        ComplexityLevel.MEDIUM,
        ComplexityLevel.TRIVIAL,
    )
