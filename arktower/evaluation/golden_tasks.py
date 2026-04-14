"""Golden test tasks — canonical examples for format validation and eval coverage."""

from __future__ import annotations

GOLDEN_TASKS: list[dict] = [
    {
        "title": "Minimal task",
        "description": "",
    },
    {
        "title": "Full featured task",
        "description": "Implement comprehensive JWT authentication with RS256 signing",
        "priority": "high",
        "tags": ["python", "auth", "api", "security"],
        "labels": {"sprint": "2026-w16", "epic": "auth-overhaul"},
        "parameters": {"repo": "git@github.com:org/api.git", "branch": "feature/jwt"},
    },
    {
        "title": "Critical production hotfix",
        "description": "Database connection pool exhaustion under load\n\n- [ ] Identify leak\n- [ ] Fix connection handling\n- [ ] Add connection pool monitoring",
        "priority": "critical",
        "tags": ["bugfix", "database", "production"],
    },
    {
        "title": "Research distributed task scheduling algorithms",
        "description": "Survey existing approaches to distributed task scheduling for multi-agent systems. "
                       "Compare: round-robin, weighted fair queuing, capability-based matching, auction-based allocation. "
                       "Produce a comparison matrix with latency, fairness, and scalability metrics.",
        "priority": "medium",
        "tags": ["research", "architecture", "distributed"],
    },
    {
        "title": "Refactor state machine to support plugins",
        "description": "Allow custom transition hooks and gate checks via plugin architecture",
        "priority": "medium",
        "tags": ["refactor", "architecture", "python"],
    },
    {
        "title": "Unicode 测试: 中文任务标题 🏰",
        "description": "确认系统正确处理中文、日文（テスト）、韩文（테스트）以及 emoji 🎉",
        "tags": ["testing", "i18n"],
    },
    {
        "title": "Add comprehensive API rate limiting",
        "description": "Implement token-bucket rate limiting for REST endpoints.\n\n"
                       "- [ ] Design rate limit configuration schema\n"
                       "- [ ] Implement middleware\n"
                       "- [ ] Add per-agent rate tracking\n"
                       "- [ ] Dashboard rate limit visualization\n"
                       "- [ ] Unit tests with 90%+ coverage\n"
                       "- [ ] Load test with concurrent agents",
        "priority": "high",
        "tags": ["api", "security", "performance"],
    },
    {
        "title": "Migrate from SQLite to PostgreSQL",
        "description": "Add PostgreSQL support as an alternative storage backend",
        "priority": "low",
        "tags": ["migration", "database", "postgresql"],
        "parameters": {"target_db": "postgresql://localhost/arktower"},
    },
    {
        "title": "Simple typo fix in README",
        "description": "Fix 'teh' -> 'the' on line 42",
        "priority": "low",
        "tags": ["documentation"],
    },
    {
        "title": "Implement MCP streaming for long-running tasks",
        "description": "Add SSE-based progress streaming for MCP tool calls that take >30s. "
                       "This requires changes to the MCP server transport layer, task service "
                       "progress reporting, and client-side handling in Cursor.",
        "priority": "high",
        "tags": ["mcp", "streaming", "performance"],
        "labels": {"complexity": "high", "estimated_hours": "16"},
    },
    {
        "title": "Empty description edge case",
        "description": "",
        "priority": "low",
        "tags": [],
    },
    {
        "title": "Task with maximum tag count",
        "description": "Testing tag handling limits",
        "tags": ["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9", "t10",
                 "t11", "t12", "t13", "t14", "t15", "t16", "t17", "t18", "t19", "t20"],
    },
]
