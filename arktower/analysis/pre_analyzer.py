"""Orchestrate complexity scoring and tag extraction for pre-analysis."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, Field

from arktower.analysis.complexity_scorer import ComplexityResult, ComplexityScorer
from arktower.analysis.tag_extractor import TagExtractor


class AnalysisResult(BaseModel):
    """Combined pre-analysis: complexity estimate and suggested tags."""

    complexity: ComplexityResult
    suggested_tags: list[str] = Field(default_factory=list)


class PreAnalyzer:
    """Run `ComplexityScorer` and `TagExtractor` together."""

    def __init__(
        self,
        scorer: ComplexityScorer | None = None,
        extractor: TagExtractor | None = None,
    ) -> None:
        self._scorer = scorer if scorer is not None else ComplexityScorer()
        self._extractor = extractor if extractor is not None else TagExtractor()

    def analyze(
        self,
        title: str,
        description: str,
        tags: Sequence[str] | None = None,
    ) -> AnalysisResult:
        tag_list = list(tags) if tags is not None else []
        complexity = self._scorer.score(title, description, tag_list)
        suggested = self._extractor.extract(title, description)
        return AnalysisResult(complexity=complexity, suggested_tags=suggested)
