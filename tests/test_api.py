from fastapi.testclient import TestClient
from api import app
from task_store import create_task, list_tasks
import pytest


client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_tasks():
    list_tasks().clear()


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_get_tasks():
    create_task("Learn FastAPI")

    response = client.get("/api/tasks")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["title"] == "Learn FastAPI"
    assert data[0]["completed"] is False


def test_create_task():
    response = client.post(
        "/api/tasks",
        json={"title": "Learn FastAPI"}
    )

    assert response.status_code == 201

    data = response.json()

    assert data["title"] == "Learn FastAPI"
    assert data["completed"] is False
    assert "id" in data


def test_update_task():
    task = create_task("Learn Python")

    response = client.patch(
        f"/api/tasks/{task.id}",
        json={"title": "Learn FastAPI"}
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Learn FastAPI"


def test_update_nonexistent_task():
    response = client.patch(
        "/api/tasks/nonexistent-id",
        json={"title": "New title"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_delete_task():
    task = create_task("Learn Python")

    response = client.delete(f"/api/tasks/{task.id}")

    assert response.status_code == 204
    assert len(list_tasks()) == 0


def test_delete_nonexistent_task():
    response = client.delete("/api/tasks/nonexistent-id")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_execute_agent(monkeypatch):
    def mock_process_request(user_request):
        return "Task created successfully"

    monkeypatch.setattr(
        "api.process_request",
        mock_process_request
    )

    response = client.post(
        "/api/agent/execute",
        json={"user_request": "Remind me to study Python"}
    )

    assert response.status_code == 200
    assert response.json() == "Task created successfully"
