"""Internationalization support for the ArkTower web dashboard (EN/ZH)."""

from __future__ import annotations

TRANSLATIONS: dict[str, dict[str, str]] = {
    # dashboard / nav
    "nav.dashboard": {"en": "DASHBOARD", "zh": "控制台"},
    "nav.task_pool": {"en": "TASK POOL", "zh": "任务池"},
    "nav.analytics": {"en": "ANALYTICS", "zh": "数据分析"},
    "nav.dependencies": {"en": "DEPENDENCIES", "zh": "依赖图"},
    "nav.navigation": {"en": "[NAVIGATION]", "zh": "[导航]"},
    "footer.system": {"en": "[YoRHa] ArkTower v0.1.0", "zh": "[YoRHa] ArkTower v0.1.0"},
    "footer.status": {"en": "Tower System Active", "zh": "塔系统运行中"},
    # pool overview
    "pool.system_status": {"en": "[SYSTEM] POOL STATUS", "zh": "[系统] 池状态"},
    "pool.total_tasks": {"en": "TOTAL TASKS", "zh": "任务总数"},
    "pool.active": {"en": "ACTIVE", "zh": "活跃"},
    "pool.blocked": {"en": "BLOCKED", "zh": "已阻塞"},
    "pool.failed": {"en": "FAILED", "zh": "已失败"},
    "pool.status_dist": {"en": "[DATA] STATUS DISTRIBUTION", "zh": "[数据] 状态分布"},
    "pool.priority_breakdown": {"en": "[DATA] PRIORITY BREAKDOWN", "zh": "[数据] 优先级分布"},
    "pool.no_data": {"en": "[NO DATA] No tasks yet", "zh": "[无数据] 暂无任务"},
    "pool.recent_feed": {"en": "[RECENT] TASK FEED", "zh": "[最新] 任务动态"},
    # task board
    "board.title": {"en": "[SYSTEM] TASK POOL", "zh": "[系统] 任务池"},
    "board.search": {"en": "SEARCH TASKS...", "zh": "搜索任务..."},
    "board.status": {"en": "STATUS", "zh": "状态"},
    "board.priority": {"en": "PRIORITY", "zh": "优先级"},
    "board.refresh": {"en": "REFRESH", "zh": "刷新"},
    "board.empty": {
        "en": "[NO DATA] No tasks match current parameters.",
        "zh": "[无数据] 没有匹配当前筛选条件的任务。",
    },
    # task detail
    "detail.error_not_found": {"en": "[ERROR] Task not found", "zh": "[错误] 任务未找到"},
    "detail.back": {"en": "< BACK TO POOL", "zh": "< 返回任务池"},
    "detail.id": {"en": "[ID]", "zh": "[编号]"},
    "detail.owner": {"en": "[OWNER]", "zh": "[所有者]"},
    "detail.assigned": {"en": "[ASSIGNED]", "zh": "[分配给]"},
    "detail.created": {"en": "[CREATED]", "zh": "[创建时间]"},
    "detail.updated": {"en": "[UPDATED]", "zh": "[更新时间]"},
    "detail.completed": {"en": "[COMPLETED]", "zh": "[完成时间]"},
    "detail.tags": {"en": "[TAGS]", "zh": "[标签]"},
    "detail.template": {"en": "[TEMPLATE]", "zh": "[模板]"},
    "detail.version": {"en": "[VERSION]", "zh": "[版本]"},
    "detail.description": {"en": "[DESCRIPTION]", "zh": "[描述]"},
    "detail.output": {"en": "[OUTPUT]", "zh": "[输出]"},
    "detail.error": {"en": "[ERROR]", "zh": "[错误]"},
    "detail.history": {"en": "[LOG] TRANSITION HISTORY", "zh": "[日志] 状态变更历史"},
    # analytics
    "analytics.title": {"en": "[ANALYTICS] TASK POOL METRICS", "zh": "[分析] 任务池指标"},
    "analytics.completion": {"en": "[METRICS] COMPLETION", "zh": "[指标] 完成情况"},
    "analytics.success_rate": {"en": "SUCCESS RATE", "zh": "成功率"},
    "analytics.no_data": {"en": "[NO DATA]", "zh": "[无数据]"},
    "analytics.no_tasks": {"en": "No completed tasks yet", "zh": "暂无已完成任务"},
    "analytics.avg_time": {"en": "AVG COMPLETION TIME", "zh": "平均完成时间"},
    "analytics.queue_health": {"en": "[STATUS] QUEUE HEALTH", "zh": "[状态] 队列健康"},
    "analytics.queued": {"en": "QUEUED", "zh": "排队中"},
    "analytics.in_progress": {"en": "IN PROGRESS", "zh": "进行中"},
    "analytics.oldest": {"en": "OLDEST QUEUED", "zh": "最久等待"},
    # dependency graph
    "graph.title": {"en": "[TOPOLOGY] DEPENDENCY GRAPH", "zh": "[拓扑] 依赖关系图"},
    "graph.empty": {"en": "[NO DATA] No tasks to display.", "zh": "[无数据] 没有可显示的任务。"},
    # priority labels
    "priority.critical": {"en": "CRITICAL", "zh": "紧急"},
    "priority.high": {"en": "HIGH", "zh": "高"},
    "priority.medium": {"en": "MEDIUM", "zh": "中"},
    "priority.low": {"en": "LOW", "zh": "低"},
}


def get_lang() -> str:
    """Return the current language from user session storage, defaulting to 'en'."""
    from nicegui import app

    try:
        return app.storage.user.get("lang", "en")
    except Exception:
        return "en"


def set_lang(lang: str) -> None:
    """Persist the chosen language into user session storage."""
    from nicegui import app

    app.storage.user["lang"] = lang


def t(key: str) -> str:
    """Translate *key* to the user's current language."""
    lang = get_lang()
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key
    return entry.get(lang, entry.get("en", key))
