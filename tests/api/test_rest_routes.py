"""Tests for REST API routes."""

from __future__ import annotations

import pytest


def _post(client, path: str, **kwargs):
    return client.post(path, json=kwargs)


class TestCreateTask:
    def test_create_minimal(self, client):
        r = _post(client, "/api/v1/tasks", title="Test task")
        assert r.status_code == 201
        data = r.json()
        assert data["title"] == "Test task"
        assert data["status"] == "submitted"
        assert data["priority"] == "medium"
        assert "id" in data

    def test_create_with_fields(self, client):
        r = _post(client, "/api/v1/tasks", title="Full", description="d", priority="high", tags=["py", "api"])
        assert r.status_code == 201
        assert r.json()["priority"] == "high"
        assert r.json()["tags"] == ["py", "api"]


class TestGetTask:
    def test_get_existing(self, client):
        tid = _post(client, "/api/v1/tasks", title="G").json()["id"]
        r = client.get(f"/api/v1/tasks/{tid}")
        assert r.status_code == 200
        assert r.json()["id"] == tid

    def test_get_not_found(self, client):
        r = client.get("/api/v1/tasks/nonexistent")
        assert r.status_code == 404
        assert r.json()["error"] == "not_found"


class TestListTasks:
    def test_list_empty(self, client):
        r = client.get("/api/v1/tasks")
        assert r.status_code == 200
        data = r.json()
        assert data["tasks"] == []
        assert data["total"] == 0

    def test_list_with_tasks(self, client):
        _post(client, "/api/v1/tasks", title="T1")
        _post(client, "/api/v1/tasks", title="T2")
        r = client.get("/api/v1/tasks")
        assert r.status_code == 200
        assert r.json()["total"] == 2

    def test_list_filter_status(self, client):
        _post(client, "/api/v1/tasks", title="T1")
        r = client.get("/api/v1/tasks", params={"status": "submitted"})
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_list_pagination(self, client):
        for i in range(3):
            _post(client, "/api/v1/tasks", title=f"T{i}")
        r = client.get("/api/v1/tasks", params={"limit": 2})
        assert r.status_code == 200
        assert len(r.json()["tasks"]) == 2


class TestUpdateTask:
    def test_patch_title(self, client):
        tid = _post(client, "/api/v1/tasks", title="old").json()["id"]
        r = client.patch(f"/api/v1/tasks/{tid}", json={"title": "new"})
        assert r.status_code == 200
        assert r.json()["title"] == "new"


class TestDeleteTask:
    def test_delete_existing(self, client):
        tid = _post(client, "/api/v1/tasks", title="del").json()["id"]
        r = client.delete(f"/api/v1/tasks/{tid}")
        assert r.status_code == 204
        assert client.get(f"/api/v1/tasks/{tid}").status_code == 404

    def test_delete_not_found(self, client):
        r = client.delete("/api/v1/tasks/missing")
        assert r.status_code == 404


class TestAdvanceTask:
    def test_enqueue(self, client):
        tid = _post(client, "/api/v1/tasks", title="Q").json()["id"]
        r = _post(client, f"/api/v1/tasks/{tid}/advance", trigger="enqueue", actor="sys")
        assert r.status_code == 200
        assert r.json()["status"] == "queued"

    def test_invalid_transition(self, client):
        tid = _post(client, "/api/v1/tasks", title="X").json()["id"]
        r = _post(client, f"/api/v1/tasks/{tid}/advance", trigger="complete", actor="sys")
        assert r.status_code == 400
        assert r.json()["error"] == "invalid_transition"

    def test_claim_via_advance_rejected(self, client):
        tid = _post(client, "/api/v1/tasks", title="X").json()["id"]
        _post(client, f"/api/v1/tasks/{tid}/advance", trigger="enqueue", actor="sys")
        r = _post(client, f"/api/v1/tasks/{tid}/advance", trigger="claim", actor="agent")
        assert r.status_code == 400
        assert "CLAIM" in r.json()["detail"]


class TestClaimAndComplete:
    def test_full_lifecycle(self, client):
        tid = _post(client, "/api/v1/tasks", title="work").json()["id"]
        _post(client, f"/api/v1/tasks/{tid}/advance", trigger="enqueue", actor="sys")

        r = _post(client, f"/api/v1/tasks/{tid}/claim", agent_id="agent-1", agent_type="bot")
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"
        assert r.json()["assigned_to"] == "agent-1"

        r = _post(client, f"/api/v1/tasks/{tid}/complete", actor="agent-1", output="done")
        assert r.status_code == 200
        assert r.json()["status"] == "completed"

    def test_double_claim_fails(self, client):
        tid = _post(client, "/api/v1/tasks", title="C").json()["id"]
        _post(client, f"/api/v1/tasks/{tid}/advance", trigger="enqueue", actor="sys")
        _post(client, f"/api/v1/tasks/{tid}/claim", agent_id="a1")
        r = _post(client, f"/api/v1/tasks/{tid}/claim", agent_id="a2")
        assert r.status_code in (400, 409)


class TestHistory:
    def test_get_history(self, client):
        tid = _post(client, "/api/v1/tasks", title="H").json()["id"]
        r = client.get(f"/api/v1/tasks/{tid}/history")
        assert r.status_code == 200
        data = r.json()
        assert data["task_id"] == tid
        assert len(data["events"]) >= 1

    def test_history_not_found(self, client):
        r = client.get("/api/v1/tasks/bad/history")
        assert r.status_code == 404


class TestPoolEndpoints:
    def test_stats(self, client):
        r = client.get("/api/v1/pool/stats")
        assert r.status_code == 200
        assert "total" in r.json()
        assert "by_status" in r.json()

    def test_next_empty(self, client):
        r = client.get("/api/v1/pool/next")
        assert r.status_code == 200
        assert r.json()["task"] is None

    def test_next_with_queued(self, client):
        tid = _post(client, "/api/v1/tasks", title="NQ").json()["id"]
        _post(client, f"/api/v1/tasks/{tid}/advance", trigger="enqueue", actor="sys")
        r = client.get("/api/v1/pool/next")
        assert r.status_code == 200
        assert r.json()["task"]["id"] == tid


class TestTemplates:
    def test_create_and_list(self, client):
        r = client.post("/api/v1/templates", json={"name": "bugfix", "description": "d", "default_tags": ["bug"]})
        assert r.status_code == 201
        r2 = client.get("/api/v1/templates")
        assert r2.status_code == 200
        assert len(r2.json()) == 1


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"
        assert data["db_ok"] is True
