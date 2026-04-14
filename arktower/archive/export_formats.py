"""Serialization helpers for archived task data."""

from __future__ import annotations

import csv
import io
import json
from typing import Any, Sequence

from pydantic import BaseModel


class ExportFormats:
    """Static helpers to export snapshots or tasks as common formats."""

    @staticmethod
    def to_json(data: Any, *, indent: int = 2) -> str:
        """Pretty-print *data* as JSON (``datetime`` values must already be JSON-safe)."""
        return json.dumps(data, indent=indent, sort_keys=True, default=_json_default)

    @staticmethod
    def to_ndjson(items: Sequence[dict[str, Any]]) -> str:
        """One JSON object per line."""
        lines: list[str] = []
        for item in items:
            lines.append(json.dumps(item, sort_keys=True, default=_json_default))
        return "\n".join(lines) + ("\n" if lines else "")

    @staticmethod
    def to_csv(rows: Sequence[dict[str, Any]], fieldnames: list[str] | None = None) -> str:
        """CSV with header from *fieldnames* or union of keys across *rows*."""
        if not rows:
            return ""
        if fieldnames is None:
            keys: set[str] = set()
            for row in rows:
                keys.update(row.keys())
            fieldnames = sorted(keys)
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue()

    @staticmethod
    def to_task_md(task: dict[str, Any] | BaseModel) -> str:
        """Render a single task as Markdown."""
        if isinstance(task, BaseModel):
            data = task.model_dump(mode="json")
        else:
            data = dict(task)
        title = data.get("title", "")
        tid = data.get("id", "")
        lines = [
            f"# {title}",
            "",
            f"- **id**: `{tid}`",
            f"- **status**: {data.get('status', '')}",
            f"- **priority**: {data.get('priority', '')}",
        ]
        desc = data.get("description") or ""
        if desc:
            lines.extend(["", "## Description", "", desc])
        out = data.get("output")
        if out:
            lines.extend(["", "## Output", "", str(out)])
        err = data.get("error")
        if err:
            lines.extend(["", "## Error", "", str(err)])
        tags = data.get("tags") or []
        if tags:
            lines.extend(["", "## Tags", "", ", ".join(str(t) for t in tags)])
        return "\n".join(lines) + "\n"


def _json_default(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
