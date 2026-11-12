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
    mock_generate = Mock(
        return_value='{"action": "create_task", "task_title": "Learn Python"}')
    monkeypatch.setattr(agent.provider, "generate", mock_generate)

    decision = agent.interpret_request("Add a task to learn Python")

    assert decision.action == "create_task"
    assert decision.task_title == "Learn Python"


def test_interpret_create_task_with_due_date(monkeypatch):
    mock_generate = Mock(
        return_value='{"action": "create_task", "task_title": "Learn Python", "due_date": "2026-11-15"}'
    )
    monkeypatch.setattr(agent.provider, "generate", mock_generate)

    decision = agent.interpret_request(
        "Add a task to learn Python by November 15")

    assert decision.action == "create_task"
    assert decision.task_title == "Learn Python"
    assert decision.due_date == date(2026, 11, 15)


def test_interpret_update_task(monkeypatch):
    mock_generate = Mock(
        return_value='{"action": "update_task", "task_id": "123", "new_title": "Study mathematics"}'
    )
    monkeypatch.setattr(agent.provider, "generate", mock_generate)

    decision = agent.interpret_request("Rename task 123 to Study mathematics")

    assert decision.action == "update_task"
    assert decision.task_id == "123"
    assert decision.new_title == "Study mathematics"


def test_interpret_clarification(monkeypatch):
    mock_generate = Mock(
        return_value='{"action": "clarify", "clarification": "Which task are you referring to?"}'
    )
    monkeypatch.setattr(agent.provider, "generate", mock_generate)

    decision = agent.interpret_request("Update my task")

    assert decision.action == "clarify"
    assert decision.clarification == "Which task are you referring to?"


def test_interpret_empty_response(monkeypatch):
    mock_generate = Mock(
        side_effect=ValueError("LLM returned an empty response")
    )
    monkeypatch.setattr(agent.provider, "generate", mock_generate)

    with pytest.raises(ValueError, match="LLM returned an empty response"):
        agent.interpret_request("Show my tasks")


def test_interpret_invalid_json(monkeypatch):
    mock_generate = Mock(return_value="This is not valid JSON")
    monkeypatch.setattr(agent.provider, "generate", mock_generate)

    with pytest.raises(ValueError):
        agent.interpret_request("Show my tasks")


def test_process_request_clarification(monkeypatch):
    decision = AgentDecision(
        action="clarify",
        clarification="Which task do you mean?"
    )

    mock_interpret = Mock(return_value=decision)
    mock_execute = Mock()

    monkeypatch.setattr(agent, "interpret_request", mock_interpret)
    monkeypatch.setattr(agent, "execute_decision", mock_execute)

    result, needs_clarification = agent.process_request(
        "Delete my task"
    )

    assert result == "Which task do you mean?"
    assert needs_clarification is True

    mock_execute.assert_not_called()


def test_process_request_success(monkeypatch):
    decision = AgentDecision(
        action="create_task",
        task_title="Learn Python"
    )

    mock_interpret = Mock(return_value=decision)
    mock_execute = Mock(return_value="Task created")

    monkeypatch.setattr(agent, "interpret_request", mock_interpret)
    monkeypatch.setattr(agent, "execute_decision", mock_execute)
    monkeypatch.setattr(agent, "get_validation_text",
                        Mock(return_value="Create a task"))

    result, needs_clarification = agent.process_request(
        "Create a task to learn Python"
    )

    assert result == "Task created"
    assert needs_clarification is False
    mock_execute.assert_called_once_with(decision)


def test_process_request_correct_date(monkeypatch):
    decision = AgentDecision(
        action="create_task",
        task_title="Study AI",
        due_date=date(2026, 11, 16)
    )

    monkeypatch.setattr(agent, "interpret_request",
                        Mock(return_value=decision))
    monkeypatch.setattr(agent, "get_validation_text", Mock(
        return_value="Create a task by Monday"))
    mock_execute = Mock(return_value="Task created")
    monkeypatch.setattr(agent, "execute_decision", mock_execute)

    monkeypatch.setattr(agent, "validate_due_date", Mock(return_value=True))

    result, needs_clarification = agent.process_request(
        "Create a task by Monday"
    )

    assert result == "Task created"
    assert needs_clarification is False
    mock_execute.assert_called_once_with(decision)


def test_process_request_date_retry_success(monkeypatch):
    first_decision = AgentDecision(
        action="create_task",
        task_title="Study AI",
        due_date=date(2026, 11, 17)
    )

    corrected_decision = AgentDecision(
        action="create_task",
        task_title="Study AI",
        due_date=date(2026, 11, 16)
    )

    mock_interpret = Mock(
        side_effect=[first_decision, corrected_decision]
    )

    mock_validate = Mock(side_effect=[False, True])
    mock_execute = Mock(return_value="Task created")

    monkeypatch.setattr(agent, "interpret_request", mock_interpret)
    monkeypatch.setattr(agent, "validate_due_date", mock_validate)
    monkeypatch.setattr(agent, "get_validation_text",
                        Mock(return_value="Monday"))
    monkeypatch.setattr(agent, "execute_decision", mock_execute)

    result, needs_clarification = agent.process_request(
        "Create a task by Monday"
    )

    assert result == "Task created"
    assert needs_clarification is False

    assert mock_interpret.call_count == 2
    assert mock_validate.call_count == 2
    mock_execute.assert_called_once_with(corrected_decision)


def test_process_request_date_retry_failure(monkeypatch):
    decision = AgentDecision(
        action="create_task",
        task_title="Study AI",
        due_date=date(2026, 11, 17)
    )

    mock_interpret = Mock(return_value=decision)
    mock_validate = Mock(return_value=False)
    mock_execute = Mock()

    monkeypatch.setattr(agent, "interpret_request", mock_interpret)
    monkeypatch.setattr(agent, "validate_due_date", mock_validate)
    monkeypatch.setattr(agent, "get_validation_text",
                        Mock(return_value="Monday"))
    monkeypatch.setattr(agent, "execute_decision", mock_execute)

    result, needs_clarification = agent.process_request(
        "Create a task by Monday"
    )

    assert isinstance(result, str)
    assert "unable to confidently determine" in result
    assert needs_clarification is True

    assert mock_interpret.call_count == 2
    mock_execute.assert_not_called()


def test_process_request_retry_clarification(monkeypatch):
    first_decision = AgentDecision(
        action="create_task",
        task_title="Study AI",
        due_date=date(2026, 11, 17)
    )

    retry_decision = AgentDecision(
        action="clarify",
        clarification="Could you confirm the date?"
    )

    mock_interpret = Mock(
        side_effect=[first_decision, retry_decision]
    )

    mock_execute = Mock()

    monkeypatch.setattr(agent, "interpret_request", mock_interpret)
    monkeypatch.setattr(agent, "validate_due_date", Mock(return_value=False))
    monkeypatch.setattr(agent, "get_validation_text",
                        Mock(return_value="Monday"))
    monkeypatch.setattr(agent, "execute_decision", mock_execute)

    result, needs_clarification = agent.process_request(
        "Create a task by Monday"
    )

    assert result == "Could you confirm the date?"
    assert needs_clarification is True

    assert mock_interpret.call_count == 2
    mock_execute.assert_not_called()
