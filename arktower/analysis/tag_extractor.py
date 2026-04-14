"""Extract suggested tags from task title and description."""

from __future__ import annotations

import re
from typing import ClassVar

# (canonical_tag, pattern) — pattern matches case-insensitive in combined text.
_TAG_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # Languages
    ("python", re.compile(r"\bpython\d?\b", re.I)),
    ("javascript", re.compile(r"\b(javascript|js)\b", re.I)),
    ("typescript", re.compile(r"\b(typescript|ts)\b", re.I)),
    ("rust", re.compile(r"\brust\b", re.I)),
    ("go", re.compile(r"\bgolang\b|\bin go\b", re.I)),
    ("java", re.compile(r"\bjava\b", re.I)),
    ("kotlin", re.compile(r"\bkotlin\b", re.I)),
    ("swift", re.compile(r"\bswift\b", re.I)),
    ("php", re.compile(r"\bphp\b", re.I)),
    ("ruby", re.compile(r"\bruby\b", re.I)),
    ("csharp", re.compile(r"\b(c#|csharp|\.net)\b", re.I)),
    ("cpp", re.compile(r"\b(c\+\+|cpp)\b", re.I)),
    ("c", re.compile(r"\bc lang(uage)?\b|\bANSI C\b", re.I)),
    ("shell", re.compile(r"\b(bash|zsh|sh|shell script)\b", re.I)),
    # Domain
    ("api", re.compile(r"\b(api|rest|graphql|grpc)\b", re.I)),
    ("auth", re.compile(r"\b(auth|oauth|jwt|sso|login|session)\b", re.I)),
    ("database", re.compile(r"\b(sql|postgres|mysql|sqlite|mongodb|redis)\b", re.I)),
    ("security", re.compile(r"\b(security|vulnerability|xss|csrf|cve)\b", re.I)),
    ("frontend", re.compile(r"\b(frontend|ui|ux|css|html|dom)\b", re.I)),
    ("backend", re.compile(r"\bbackend\b", re.I)),
    ("devops", re.compile(r"\b(devops|ci\s*/\s*cd|pipeline|deploy)\b", re.I)),
    ("testing", re.compile(r"\b(test|pytest|jest|mocha|unit test|e2e)\b", re.I)),
    ("docker", re.compile(r"\b(docker|kubernetes|k8s|helm)\b", re.I)),
    # Frameworks
    ("react", re.compile(r"\breact(\.js)?\b", re.I)),
    ("vue", re.compile(r"\bvue(\.js)?\b", re.I)),
    ("angular", re.compile(r"\bangular\b", re.I)),
    ("svelte", re.compile(r"\bsvelte\b", re.I)),
    ("django", re.compile(r"\bdjango\b", re.I)),
    ("flask", re.compile(r"\bflask\b", re.I)),
    ("fastapi", re.compile(r"\bfastapi\b", re.I)),
    ("rails", re.compile(r"\b(rails|ruby on rails)\b", re.I)),
    ("spring", re.compile(r"\bspring (boot|mvc)?\b", re.I)),
    ("express", re.compile(r"\bexpress(\.js)?\b", re.I)),
    ("nextjs", re.compile(r"\bnext(\.js)?\b", re.I)),
]


class TagExtractor:
    """Pull language, domain, and framework tags from free text."""

    _patterns: ClassVar[list[tuple[str, re.Pattern[str]]]] = _TAG_PATTERNS

    def extract(self, title: str, description: str) -> list[str]:
        text = f"{title}\n{description}"
        seen: set[str] = set()
        ordered: list[str] = []
        for tag, pat in self._patterns:
            if tag in seen:
                continue
            if pat.search(text):
                seen.add(tag)
                ordered.append(tag)
        return ordered
