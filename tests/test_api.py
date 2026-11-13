from fastapi.testclient import TestClient

import task_store as store
from api import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "healthy"}


def test_task_crud_flow():
    r = client.post(
        "/api/tasks", json={"title": "Write report", "due_date": "2030-05-01"})
    assert r.status_code == 201
    task = r.json()
    assert task["completed"] is False

    assert client.get("/api/tasks").json() == [task]
    assert client.get(f"/api/tasks/{task['id']}").json() == task

    r = client.patch(f"/api/tasks/{task['id']}", json={"completed": True})
    assert r.status_code == 200 and r.json()["completed"] is True

    assert client.delete(f"/api/tasks/{task['id']}").status_code == 204
    assert client.get("/api/tasks").json() == []


def test_not_found():
    assert client.get("/api/tasks/x").status_code == 404
    assert client.patch("/api/tasks/x", json={"title": "a"}).status_code == 404
    assert client.delete("/api/tasks/x").status_code == 404


def test_validation_errors():
    assert client.post("/api/tasks", json={"title": ""}).status_code == 422
    assert client.post("/api/tasks", json={"title": "   "}).status_code == 422
    assert client.post(
        "/api/tasks", json={"title": "a", "due_date": "bad"}).status_code == 422
    assert client.post("/api/tasks", json={}).status_code == 422


def test_patch_requires_a_field():
    task = store.create_task("A")
    assert client.patch(f"/api/tasks/{task.id}", json={}).status_code == 400


def test_agent_endpoint(llm):
    llm.add(action="create_task", task_title="Buy milk")
    r = client.post("/api/agent/execute",
                    json={"user_request": "add buy milk"})
    body = r.json()
    assert r.status_code == 200
    assert body["needs_clarification"] is False
    assert body["task"]["title"] == "Buy milk"


def test_agent_endpoint_clarification_with_history(llm):
    llm.add(action="clarify", clarification="Which task?")
    r = client.post("/api/agent/execute", json={"user_request": "delete it"})
    assert r.json()["needs_clarification"] is True

    llm.add(action="create_task", task_title="Call mom")
    r = client.post("/api/agent/execute", json={
        "user_request": "call mom",
        "history": ["User: add a task", "TaskPilot: What is it?"],
    })
    assert r.json()["task"]["title"] == "Call mom"


def test_agent_endpoint_validation_and_llm_failure(llm):
    assert client.post("/api/agent/execute",
                       json={"user_request": ""}).status_code == 422
    llm.queue.append(ConnectionError("down"))
    r = client.post("/api/agent/execute", json={"user_request": "hi"})
    assert r.status_code == 502
