"""Heuristic task complexity scoring from title, description, and tags."""

from __future__ import annotations

import enum
import re
from collections.abc import Sequence

from pydantic import BaseModel, Field, field_validator

# Words that suggest higher conceptual or integration complexity (lowercased).
_COMPLEXITY_KEYWORDS: frozenset[str] = frozenset(
    {
        "refactor",
        "migrate",
        "migration",
        "architecture",
        "integrate",
        "integration",
        "dependencies",
        "dependency",
        "distributed",
        "concurrent",
        "race",
        "deadlock",
        "scalability",
        "performance",
        "optimization",
        "security",
        "authentication",
        "authorization",
        "encryption",
        "compliance",
        "multi",
        "cross",
        "breaking",
        "backward",
        "compatibility",
        "legacy",
        "rewrite",
        "orchestr",
    }
)

_CHECKBOX_LINE = re.compile(
    r"(?m)^\s*(?:[-*+]|\d+\.)\s+\[[ xX]\]",
)


class ComplexityLevel(str, enum.Enum):
    TRIVIAL = "trivial"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class ComplexityResult(BaseModel):
    """Structured complexity estimate for a task."""

    level: ComplexityLevel
    score: float = Field(ge=0.0, le=1.0)
    factors: list[str] = Field(default_factory=list)

    @field_validator("score")
    @classmethod
    def round_score(cls, v: float) -> float:
        return round(v, 4)


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _length_component(total_chars: int) -> tuple[float, str]:
    """Map combined text length to a 0–1 contribution."""
    if total_chars <= 120:
        return 0.0, "short text (≤120 chars): baseline load"
    if total_chars <= 400:
        t = (total_chars - 120) / 280
        return 0.15 + 0.25 * t, f"moderate length ({total_chars} chars)"
    if total_chars <= 2000:
        t = (total_chars - 400) / 1600
        return 0.4 + 0.35 * t, f"long description ({total_chars} chars)"
    return 1.0, f"very long text ({total_chars} chars)"


def _checkbox_component(description: str) -> tuple[float, str]:
    n = len(_CHECKBOX_LINE.findall(description))
    if n == 0:
        return 0.0, "no checklist items"
    if n <= 3:
        return 0.2 + 0.1 * (n - 1), f"{n} checklist item(s)"
    if n <= 10:
        t = (n - 3) / 7
        return 0.4 + 0.35 * t, f"{n} checklist items"
    return 1.0, f"{n} checklist items (large checklist)"


def _keyword_density_component(text: str) -> tuple[float, str]:
    lowered = text.lower()
    words = re.findall(r"[a-zA-Z]{3,}", lowered)
    word_count = max(len(words), 1)
    hits = sum(1 for w in words if w in _COMPLEXITY_KEYWORDS)
    # Scale so ~1 hit per 12 words approaches high density.
    density = min(1.0, (hits / word_count) * 12.0)
    factor = (
        f"complexity keyword density: {hits} keyword match(es) / {word_count} word(s)"
    )
    return _clamp01(density), factor


def _tags_component(tags: Sequence[str]) -> tuple[float, str]:
    n = len(tags)
    if n == 0:
        return 0.0, "no tags"
    if n <= 2:
        return 0.05 * n, f"{n} tag(s)"
    if n <= 6:
        return 0.1 + 0.08 * (n - 2), f"{n} tags"
    return 0.5, f"{n} tags (broad scope)"


class ComplexityScorer:
    """Score task complexity using length, checklist size, and keyword signals."""

    def score(
        self,
        title: str,
        description: str,
        tags: Sequence[str] | None = None,
    ) -> ComplexityResult:
        tags = list(tags) if tags is not None else []
        combined = f"{title}\n{description}".strip()
        total_chars = len(combined)

        len_score, len_factor = _length_component(total_chars)
        cb_score, cb_factor = _checkbox_component(description)
        kw_score, kw_factor = _keyword_density_component(combined)
        tag_score, tag_factor = _tags_component(tags)

        # Weighted blend: length and checklist carry most weight; tags are a light nudge.
        raw = (
            0.52 * len_score
            + 0.22 * cb_score
            + 0.22 * kw_score
            + 0.04 * tag_score
        )
        score = _clamp01(raw)

        level = self._level_for_score(score)
        factors = [len_factor, cb_factor, kw_factor, tag_factor]
        return ComplexityResult(level=level, score=score, factors=factors)

    @staticmethod
    def _level_for_score(score: float) -> ComplexityLevel:
        if score < 0.2:
            return ComplexityLevel.TRIVIAL
        if score < 0.4:
            return ComplexityLevel.LOW
        if score < 0.6:
            return ComplexityLevel.MEDIUM
        if score < 0.8:
            return ComplexityLevel.HIGH
        return ComplexityLevel.EXTREME
