from datetime import date
from unittest.mock import Mock

import agent
from models import AgentDecision

from types import SimpleNamespace

import pytest

from pydantic import ValidationError


def test_execute_create_task(monkeypatch):
    mock_create_task = Mock(return_value="Task created")

    monkeypatch.setattr(
        agent,
        "create_task",
        mock_create_task
    )

    decision = AgentDecision(
        action="create_task",
        task_title="Learn Python",
        due_date=date(2026, 11, 20)
    )

    result = agent.execute_decision(decision)

    mock_create_task.assert_called_once_with(
        title="Learn Python",
        due_date=date(2026, 11, 20)
    )

    assert result == "Task created"


def test_execute_update_task(monkeypatch):
    mock_update_task = Mock(return_value="Task updated")

    monkeypatch.setattr(agent, "update_task", mock_update_task)

    decision = AgentDecision(
        action="update_task",
        task_id="123",
        new_title="Learn Java"
    )

    result = agent.execute_decision(decision)

    mock_update_task.assert_called_once_with(
        task_id="123",
        new_title="Learn Java",
        new_due_date=None
    )

    assert result == "Task updated"


def test_execute_delete_task(monkeypatch):
    mock_delete_task = Mock(return_value=True)

    monkeypatch.setattr(agent, "delete_task", mock_delete_task)

    decision = AgentDecision(
        action="delete_task",
        task_id="123"
    )

    result = agent.execute_decision(decision)

    mock_delete_task.assert_called_once_with("123")

    assert result is True


def test_execute_complete_task(monkeypatch):
    mock_complete_task = Mock(return_value="Task completed")

    monkeypatch.setattr(agent, "complete_task", mock_complete_task)

    decision = AgentDecision(
        action="complete_task",
        task_id="123"
    )

    result = agent.execute_decision(decision)

    mock_complete_task.assert_called_once_with("123")

    assert result == "Task completed"


def test_execute_list_tasks(monkeypatch):
    mock_list_tasks = Mock(return_value=[])

    monkeypatch.setattr(agent, "list_tasks", mock_list_tasks)

    decision = AgentDecision(
        action="list_tasks"
    )

    result = agent.execute_decision(decision)

    mock_list_tasks.assert_called_once_with()

    assert result == []


def test_execute_update_without_task_id(monkeypatch):
    mock_update_task = Mock()

    monkeypatch.setattr(agent, "update_task", mock_update_task)

    decision = AgentDecision(
        action="update_task"
    )

    result = agent.execute_decision(decision)

    assert result == "Task ID is missing."
    mock_update_task.assert_not_called()


def test_interpret_create_task(monkeypatch):

    fake_response = SimpleNamespace(
        message=SimpleNamespace(
            content='{"action": "create_task", "task_title": "Learn Python"}'
        )
    )

    mock_chat = Mock(return_value=fake_response)

    monkeypatch.setattr(agent, "chat", mock_chat)

    decision = agent.interpret_request("Create a task to learn Python")

    assert decision.action == "create_task"
    assert decision.task_title == "Learn Python"

    mock_chat.assert_called_once()


def test_interpret_create_task_with_due_date(monkeypatch):
    fake_response = SimpleNamespace(
        message=SimpleNamespace(
            content='{"action": "create_task", "task_title": "Study AI", "due_date": "2026-11-20"}'
        )
    )

    mock_chat = Mock(return_value=fake_response)
    monkeypatch.setattr(agent, "chat", mock_chat)

    decision = agent.interpret_request(
        "Create a task to study AI by November 20")

    assert decision.action == "create_task"
    assert decision.task_title == "Study AI"
    assert decision.due_date == date(2026, 11, 20)


def test_interpret_update_task(monkeypatch):
    fake_response = SimpleNamespace(
        message=SimpleNamespace(
            content='{"action": "update_task", "task_id": "123", "new_title": "Learn Java"}'
        )
    )

    mock_chat = Mock(return_value=fake_response)
    monkeypatch.setattr(agent, "chat", mock_chat)

    decision = agent.interpret_request("Rename my task to Learn Java")

    assert decision.action == "update_task"
    assert decision.task_id == "123"
    assert decision.new_title == "Learn Java"


def test_interpret_clarification(monkeypatch):
    fake_response = SimpleNamespace(
        message=SimpleNamespace(
            content='{"action": "clarify", "clarification": "Which task do you mean?"}'
        )
    )

    mock_chat = Mock(return_value=fake_response)
    monkeypatch.setattr(agent, "chat", mock_chat)

    decision = agent.interpret_request("Delete my task")

    assert decision.action == "clarify"
    assert decision.clarification == "Which task do you mean?"


def test_interpret_empty_response(monkeypatch):
    fake_response = SimpleNamespace(
        message=SimpleNamespace(content=None)
    )

    mock_chat = Mock(return_value=fake_response)
    monkeypatch.setattr(agent, "chat", mock_chat)

    with pytest.raises(ValueError):
        agent.interpret_request("Create a task")


def test_interpret_invalid_json(monkeypatch):
    fake_response = SimpleNamespace(
        message=SimpleNamespace(
            content="This is not valid JSON"
        )
    )

    mock_chat = Mock(return_value=fake_response)
    monkeypatch.setattr(agent, "chat", mock_chat)

    with pytest.raises(ValidationError):
        agent.interpret_request("Create a task")
