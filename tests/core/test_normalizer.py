"""Tests for arktower.core.normalizer.TaskNormalizer."""

from __future__ import annotations

from arktower.core.models import TaskPriority
from arktower.core.normalizer import TaskNormalizer


class TestTaskNormalizer:
    def setup_method(self):
        self.normalizer = TaskNormalizer()

    def test_empty_input_returns_untitled(self):
        result = self.normalizer.normalize("")
        assert result.title == "Untitled task"

    def test_single_line_becomes_title(self):
        result = self.normalizer.normalize("Fix login bug")
        assert result.title == "Fix login bug"
        assert result.description == ""

    def test_multiline_splits_title_description(self):
        raw = "Implement auth module\nUse JWT tokens for session management\nAdd rate limiting"
        result = self.normalizer.normalize(raw)
        assert result.title == "Implement auth module"
        assert "JWT tokens" in result.description
        assert "rate limiting" in result.description

    def test_critical_keyword_sets_priority(self):
        result = self.normalizer.normalize("URGENT: fix production outage")
        assert result.priority == TaskPriority.CRITICAL

    def test_high_keyword_sets_priority(self):
        result = self.normalizer.normalize("Important security patch\nMust have before release")
        assert result.priority == TaskPriority.HIGH

    def test_low_keyword_sets_priority(self):
        result = self.normalizer.normalize("Nice to have: update readme")
        assert result.priority == TaskPriority.LOW

    def test_no_keyword_defaults_medium(self):
        result = self.normalizer.normalize("Refactor database layer")
        assert result.priority == TaskPriority.MEDIUM

    def test_tags_extracted_from_content(self):
        result = self.normalizer.normalize(
            "Build FastAPI endpoint\nUse Python and PostgreSQL for storage"
        )
        assert "python" in result.tags or "fastapi" in result.tags

    def test_whitespace_stripped(self):
        result = self.normalizer.normalize("  \n  Deploy to staging  \n  Use Docker\n  ")
        assert result.title == "Deploy to staging"
        assert "Docker" in result.description

    def test_blocker_keyword_critical(self):
        result = self.normalizer.normalize("Blocker: DB connection pool exhausted")
        assert result.priority == TaskPriority.CRITICAL
