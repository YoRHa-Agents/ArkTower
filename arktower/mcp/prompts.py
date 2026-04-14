"""MCP prompt templates for ArkTower."""

from __future__ import annotations

CREATE_TASK_PROMPT = """You are creating a task in the ArkTower task pool.

Please provide:
1. A clear, concise title for the task
2. A detailed description including:
   - Objective: What needs to be accomplished
   - Background: Any relevant context
   - Acceptance Criteria: Specific, testable conditions for completion
3. Priority level: critical, high, medium, or low
4. Relevant tags (e.g., python, api, bugfix, refactor)

Use the create_task tool to submit the task."""

ANALYZE_TASK_PROMPT = """You are analyzing a task from the ArkTower task pool.

Task ID: {task_id}

Please analyze this task and provide:
1. Complexity assessment (trivial/low/medium/high/extreme)
2. Estimated effort
3. Suggested decomposition into subtasks (if applicable)
4. Required capabilities/tools
5. Potential blockers or risks

Use the get_task tool to fetch the task details first."""
