from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

import agent
import task_store as store
from api import app
from tests.conftest import next_weekday

TOMORROW = date.today() + timedelta(days=1)


def create(title, due=TOMORROW):
    return {"action": "create_task", "task_title": title,
            "due_date": due.isoformat()}


# ---- the motivating example ----------------------------------------------

def test_three_tasks_all_due_tomorrow(llm):
    llm.add_plan(create("Studying"), create("Playing"), create("Presenting"))
    resp = agent.process_request(
        "add three tasks: studying, playing and presenting, all due tomorrow"
    )
    assert resp.action == "multiple"
    assert not resp.needs_clarification
    assert resp.message.count("Created task") == 3
    assert resp.tasks is not None
    assert [t.title for t in resp.tasks] == [
        "Studying", "Playing", "Presenting"]
    assert len(store.list_tasks()) == 3
    assert all(t.due_date == TOMORROW for t in store.list_tasks())


def test_complete_existing_task_and_create_others(llm):
    project = store.create_task("Python project")
    llm.add_plan(
        {"action": "complete_task", "task_id": project.id},
        create("Studying"),
        create("Playing"),
    )
    resp = agent.process_request(
        "I've completed my Python project. Add studying and playing for tomorrow"
    )
    assert not resp.needs_clarification
    tasks = {t.title: t for t in store.list_tasks()}
    assert tasks["Python project"].completed is True
    assert set(tasks) == {"Python project", "Studying", "Playing"}


def test_note_is_appended(llm):
    llm.add_plan(
        create("Studying"), create("Playing"),
        note="I couldn't find a task called 'Python project'.",
    )
    resp = agent.process_request("I finished my Python project, add two tasks")
    assert "Note: I couldn't find a task called 'Python project'." in resp.message
    assert len(store.list_tasks()) == 2


def test_note_on_single_action(llm):
    llm.add_plan(create("Studying"), note="Heads up.")
    resp = agent.process_request("add studying tomorrow")
    assert resp.action == "create_task"
    assert resp.message.endswith("Note: Heads up.")


# ---- all or nothing -------------------------------------------------------

def test_one_bad_action_blocks_the_whole_plan(llm):
    llm.add_plan(
        create("Studying"),
        {"action": "delete_task", "task_id": "made-up"},
    )
    resp = agent.process_request("add studying and delete the other one")
    assert resp.needs_clarification
    assert store.list_tasks() == []


def test_clarify_mixed_with_actions_runs_nothing(llm):
    llm.add_plan(
        create("Studying"),
        {"action": "clarify", "clarification": "Which task do you mean?"},
    )
    resp = agent.process_request("add studying and delete it")
    assert resp.needs_clarification
    assert resp.message == "Which task do you mean?"
    assert store.list_tasks() == []


# ---- weekdays in multi-task requests -------------------------------------

def test_validate_due_date_any_weekday_mode():
    monday = next_weekday("monday")
    text = "gym on monday and study on friday"
    assert not agent.validate_due_date(
        text, monday)  # latest_only: friday wins
    assert agent.validate_due_date(text, monday, latest_only=False)
    assert not agent.validate_due_date(
        text, next_weekday("wednesday"), latest_only=False)


def test_different_weekdays_in_one_plan(llm):
    llm.add_plan(
        create("Gym", next_weekday("monday")),
        create("Study", next_weekday("friday")),
    )
    resp = agent.process_request("gym on monday and study on friday")
    assert not resp.needs_clarification
    assert len(store.list_tasks()) == 2


def test_wrong_weekday_in_plan_is_retried(llm):
    llm.add_plan(
        create("Gym", next_weekday("wednesday")),
        create("Study", next_weekday("friday")),
    )
    llm.add_plan(
        create("Gym", next_weekday("monday")),
        create("Study", next_weekday("friday")),
    )
    resp = agent.process_request("gym on monday and study on friday")
    assert not resp.needs_clarification
    assert len(llm.calls) == 2
    assert len(store.list_tasks()) == 2


# ---- malformed plans ------------------------------------------------------

def test_empty_plan_is_rejected(llm):
    llm.queue.append({"actions": []})
    with pytest.raises(agent.AgentError):
        agent.process_request("hi")




# ---- API ------------------------------------------------------------------

def test_api_returns_all_results(llm):
    llm.add_plan(create("Studying"), create("Playing"), create("Presenting"))
    client = TestClient(app)
    r = client.post("/api/agent/execute", json={
        "user_request": "add three tasks: studying, playing, presenting, due tomorrow"
    })
    body = r.json()
    assert r.status_code == 200
    assert body["action"] == "multiple"
    assert [t["title"] for t in body["tasks"]] == [
        "Studying", "Playing", "Presenting"]
