"""Evaluation runner — orchestrates all evaluators and produces a report."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from arktower.evaluation.dimensions import DimensionScore, EvalDimension, EvalReport
from arktower.evaluation.evaluators import ALL_EVALUATORS, BaseEvaluator, EvalContext

logger = logging.getLogger(__name__)


class EvalRunner:
    """Run evaluation across all or selected dimensions."""

    def __init__(self, evaluators: list[BaseEvaluator] | None = None) -> None:
        self._evaluators = evaluators or [cls() for cls in ALL_EVALUATORS]

    def run(self, ctx: EvalContext) -> EvalReport:
        report = EvalReport()
        for ev in self._evaluators:
            logger.info("Evaluating: %s", ev.dimension.value)
            try:
                score = ev.evaluate(ctx)
                report.dimensions.append(score)
                logger.info(
                    "  %s: %.2f (%d passed, %d failed)",
                    ev.dimension.value, score.score, score.passed, score.failed,
                )
            except Exception as exc:
                logger.error("Evaluator %s failed: %s", ev.dimension.value, exc)
                report.dimensions.append(DimensionScore(
                    dimension=ev.dimension, score=0.0, failed=1,
                    details=[f"EVALUATOR CRASH: {exc}"],
                ))

        report.compute_overall()
        report.collect_findings()
        report.recommendations = self._generate_recommendations(report)
        return report

    def run_dimension(self, dimension: EvalDimension, ctx: EvalContext) -> DimensionScore:
        for ev in self._evaluators:
            if ev.dimension == dimension:
                return ev.evaluate(ctx)
        raise ValueError(f"No evaluator for dimension: {dimension}")

    def _generate_recommendations(self, report: EvalReport) -> list[str]:
        recs: list[str] = []
        severity_counts = report.severity_counts()

        if severity_counts.get("blocker", 0) > 0:
            recs.append("FIX BLOCKERS: Address all blocker-severity findings before proceeding")

        for ds in sorted(report.dimensions, key=lambda d: d.score):
            if ds.score < 0.8:
                recs.append(
                    f"Improve {ds.dimension.value}: score {ds.score:.2f} "
                    f"({ds.failed} failures) — target ≥0.80"
                )

        if report.overall_score >= 0.85:
            recs.append("Overall score meets standard gate threshold (≥0.85)")
        elif report.overall_score >= 0.70:
            recs.append("Overall score meets relaxed gate threshold but below standard (≥0.85)")
        else:
            recs.append("Overall score below relaxed threshold — significant improvements needed")

        return recs


def run_and_save(ctx: EvalContext, output_dir: Path | None = None) -> EvalReport:
    """Run full evaluation and optionally save the report."""
    runner = EvalRunner()
    report = runner.run(ctx)

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / f"eval_report_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.json"
        report_path.write_text(
            json.dumps(report.model_dump(mode="json"), indent=2, default=str),
            encoding="utf-8",
        )
        logger.info("Report saved to %s", report_path)

    return report


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ctx = EvalContext()
    report = run_and_save(ctx, output_dir=Path(".local/eval_reports"))

    print(f"\n{'='*60}")
    print("ArkTower Self-Evaluation Report")
    print(f"{'='*60}")
    print(f"Overall Score: {report.overall_score:.4f}")
    print(f"Timestamp: {report.timestamp}")
    print()
    for ds in report.dimensions:
        bar = "█" * int(ds.score * 20) + "░" * (20 - int(ds.score * 20))
        print(f"  {ds.dimension.value:<28} {bar} {ds.score:.2f}  ({ds.passed}P/{ds.failed}F)")
    print()
    print("Findings:")
    for f in report.findings:
        print(f"  [{f.severity.upper()}] {f.title}")
    print()
    print("Recommendations:")
    for r in report.recommendations:
        print(f"  • {r}")

    sys.exit(0 if report.overall_score >= 0.70 else 1)
