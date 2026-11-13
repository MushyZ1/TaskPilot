from datetime import date, timedelta

import pytest

import agent
import task_store as store
from tests.conftest import next_weekday

TOMORROW = date.today() + timedelta(days=1)


# ---- validate_due_date ----------------------------------------------------

def test_validate_due_date_no_weekday_or_no_date():
    assert agent.validate_due_date("buy milk", date(2030, 1, 1))
    assert agent.validate_due_date("on friday", None)


def test_validate_due_date_matches_weekday():
    friday = next_weekday("friday")
    assert agent.validate_due_date("due Friday", friday)
    assert not agent.validate_due_date("due Monday", friday)


def test_validate_due_date_uses_latest_weekday():
    friday = next_weekday("friday")
    assert agent.validate_due_date("monday... no, friday", friday)


def test_get_validation_text_only_user_messages():
    ctx = ["User: due monday", "TaskPilot: which friday?", "User: friday"]
    assert agent.get_validation_text("friday", ctx) == "due monday\nfriday"


# ---- process_request: happy paths ----------------------------------------

def test_create_task(llm):
    llm.add(action="create_task", task_title="Buy milk",
            due_date=TOMORROW.isoformat())
    resp = agent.process_request("add buy milk tomorrow")
    assert not resp.needs_clarification
    assert resp.task is not None
    assert resp.task.title == "Buy milk"
    assert store.list_tasks()[0].due_date == TOMORROW


def test_list_tasks_empty_and_non_empty(llm):
    llm.add(action="list_tasks")
    resp = agent.process_request("what do I have?")
    assert resp.message == "You have no tasks yet."

    store.create_task("A")
    llm.add(action="list_tasks")
    resp = agent.process_request("list")
    assert resp.tasks is not None
    assert len(resp.tasks) == 1


def test_update_complete_delete(llm):
    task = store.create_task("Report")

    llm.add(action="update_task", task_id=task.id, new_title="Final report")
    resp = agent.process_request("rename")
    assert resp.task is not None
    assert resp.task.title == "Final report"

    llm.add(action="complete_task", task_id=task.id)
    resp = agent.process_request("done")
    assert resp.task is not None
    assert resp.task.completed

    llm.add(action="delete_task", task_id=task.id)
    resp = agent.process_request("delete it")
    assert resp.message.startswith("Deleted")
    assert store.list_tasks() == []


def test_existing_tasks_are_sent_to_llm(llm):
    store.create_task("Dentist")
    llm.add(action="list_tasks")
    agent.process_request("list")
    assert "Dentist" in llm.calls[0][0]["content"]


# ---- clarification --------------------------------------------------------

def test_llm_clarify(llm):
    llm.add(action="clarify", clarification="Which task?")
    resp = agent.process_request("delete it")
    assert resp.needs_clarification and resp.message == "Which task?"


def test_history_is_passed_to_llm(llm):
    llm.add(action="create_task", task_title="Call mom")
    agent.process_request(
        "friday", history=["User: call mom", "TaskPilot: when?"])
    sent = llm.calls[0][1]["content"]
    assert "call mom" in sent and "User: friday" in sent


# ---- safety checks --------------------------------------------------------

@pytest.mark.parametrize("action", ["update_task", "delete_task", "complete_task"])
def test_hallucinated_task_id_asks_for_clarification(llm, action):
    store.create_task("Real")
    llm.add(action=action, task_id="made-up", new_title="x")
    resp = agent.process_request("do something")
    assert resp.needs_clarification
    assert len(store.list_tasks()) == 1


def test_create_without_title_asks_for_clarification(llm):
    llm.add(action="create_task")
    assert agent.process_request("add a task").needs_clarification


def test_update_without_changes_asks_for_clarification(llm):
    task = store.create_task("A")
    llm.add(action="update_task", task_id=task.id)
    assert agent.process_request("update A").needs_clarification


def test_past_due_date_rejected(llm):
    llm.add(action="create_task", task_title="Old",
            due_date=(date.today() - timedelta(days=3)).isoformat())
    resp = agent.process_request("add old task")
    assert resp.needs_clarification and "past" in resp.message
    assert store.list_tasks() == []


# ---- weekday retry --------------------------------------------------------

def test_weekday_mismatch_is_retried(llm):
    llm.add(action="create_task", task_title="Gym",
            due_date=next_weekday("monday").isoformat())
    llm.add(action="create_task", task_title="Gym",
            due_date=next_weekday("friday").isoformat())
    resp = agent.process_request("gym on friday")
    assert resp.task is not None
    assert resp.task.due_date == next_weekday("friday")
    assert "IMPORTANT CORRECTION" in llm.calls[1][0]["content"]


def test_weekday_mismatch_twice_gives_up(llm):
    for _ in range(2):
        llm.add(action="create_task", task_title="Gym",
                due_date=next_weekday("monday").isoformat())
    resp = agent.process_request("gym on friday")
    assert resp.needs_clarification
    assert store.list_tasks() == []


# ---- failures -------------------------------------------------------------

def test_invalid_json_raises_agent_error(llm):
    llm.queue.append("not json")
    with pytest.raises(agent.AgentError):
        agent.process_request("hi")


def test_unknown_action_raises_agent_error(llm):
    llm.add(action="launch_rocket")
    with pytest.raises(agent.AgentError):
        agent.process_request("hi")


def test_provider_failure_raises_agent_error(llm):
    llm.queue.append(ConnectionError("down"))
    with pytest.raises(agent.AgentError):
        agent.process_request("hi")
