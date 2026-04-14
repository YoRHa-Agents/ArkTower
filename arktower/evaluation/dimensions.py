"""Evaluation dimensions, scoring models, and report structure."""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class EvalDimension(str, enum.Enum):
    LIFECYCLE_CORRECTNESS = "lifecycle_correctness"
    TASK_FORMAT_QUALITY = "task_format_quality"
    DISPATCH_RELIABILITY = "dispatch_reliability"
    SEARCH_EFFECTIVENESS = "search_effectiveness"
    API_COMPLETENESS = "api_completeness"
    ANALYSIS_ACCURACY = "analysis_accuracy"
    ARCHIVE_INTEGRITY = "archive_integrity"
    CONCURRENCY_SAFETY = "concurrency_safety"


DIMENSION_WEIGHTS: dict[EvalDimension, float] = {
    EvalDimension.LIFECYCLE_CORRECTNESS: 0.20,
    EvalDimension.TASK_FORMAT_QUALITY: 0.15,
    EvalDimension.DISPATCH_RELIABILITY: 0.20,
    EvalDimension.SEARCH_EFFECTIVENESS: 0.10,
    EvalDimension.API_COMPLETENESS: 0.10,
    EvalDimension.ANALYSIS_ACCURACY: 0.10,
    EvalDimension.ARCHIVE_INTEGRITY: 0.10,
    EvalDimension.CONCURRENCY_SAFETY: 0.05,
}


class EvalFinding(BaseModel):
    severity: str
    dimension: EvalDimension
    title: str
    description: str
    file_path: str | None = None
    suggestion: str | None = None


class DimensionScore(BaseModel):
    dimension: EvalDimension
    score: float
    max_score: float = 1.0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    details: list[str] = Field(default_factory=list)
    findings: list[EvalFinding] = Field(default_factory=list)


class EvalReport(BaseModel):
    version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    dimensions: list[DimensionScore] = Field(default_factory=list)
    overall_score: float = 0.0
    findings: list[EvalFinding] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def compute_overall(self) -> float:
        if not self.dimensions:
            return 0.0
        total = 0.0
        for ds in self.dimensions:
            weight = DIMENSION_WEIGHTS.get(ds.dimension, 0.1)
            total += ds.score * weight
        self.overall_score = round(total, 4)
        return self.overall_score

    def collect_findings(self) -> list[EvalFinding]:
        all_findings: list[EvalFinding] = []
        for ds in self.dimensions:
            all_findings.extend(ds.findings)
        self.findings = all_findings
        return all_findings

    def severity_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in self.findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
        return counts
