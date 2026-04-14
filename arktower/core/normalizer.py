"""Task normalization pipeline: raw text → structured TaskCreate."""

from __future__ import annotations

import re

from arktower.analysis.tag_extractor import TagExtractor
from arktower.core.models import TaskCreate, TaskPriority

_PRIORITY_KEYWORDS: dict[TaskPriority, list[str]] = {
    TaskPriority.CRITICAL: [
        "urgent", "critical", "emergency", "asap", "p0", "blocker", "showstopper",
    ],
    TaskPriority.HIGH: [
        "important", "high priority", "high-priority", "p1", "must have", "must-have",
    ],
    TaskPriority.LOW: [
        "low priority", "low-priority", "nice to have", "nice-to-have",
        "backlog", "eventually", "p3", "minor",
    ],
}

_PRIORITY_PATTERNS: list[tuple[TaskPriority, re.Pattern[str]]] = [
    (prio, re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE))
    for prio, keywords in _PRIORITY_KEYWORDS.items()
    for kw in keywords
]


class TaskNormalizer:
    """Convert free-form text into a structured :class:`TaskCreate`."""

    def __init__(self, tag_extractor: TagExtractor | None = None) -> None:
        self._tag_extractor = tag_extractor or TagExtractor()

    def normalize(self, raw_text: str) -> TaskCreate:
        """Parse *raw_text* into a ``TaskCreate``.

        - First non-blank line becomes the title.
        - Remaining lines become the description.
        - Priority is inferred from keyword scanning.
        - Tags are extracted via :class:`TagExtractor`.
        """
        lines = raw_text.strip().splitlines()
        if not lines:
            return TaskCreate(title="Untitled task")

        title = lines[0].strip()
        description = "\n".join(lines[1:]).strip()
        priority = self._infer_priority(title, description)
        tags = self._tag_extractor.extract(title, description)

        return TaskCreate(
            title=title,
            description=description,
            priority=priority,
            tags=tags,
        )

    @staticmethod
    def _infer_priority(title: str, description: str) -> TaskPriority:
        text = f"{title}\n{description}"
        for prio, pattern in _PRIORITY_PATTERNS:
            if pattern.search(text):
                return prio
        return TaskPriority.MEDIUM
