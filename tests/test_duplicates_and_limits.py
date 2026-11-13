from datetime import date, timedelta

import pytest
from pydantic import ValidationError

import agent
from models import MAX_ACTIONS, AgentDecision, AgentPlan
from task_store import list_tasks, reset_tasks


@pytest.fixture(autouse=True)
def clean_store():
    reset_tasks()
    agent._pending_duplicates.clear()
    yield
    reset_tasks()


def use_plan(monkeypatch, plan: AgentPlan) -> None:
    """Make the agent 'receive' this plan from the LLM."""
    monkeypatch.setattr(agent, "interpret_request", lambda *a, **k: plan)


def create(title: str, due: date | None = None) -> AgentDecision:
    return AgentDecision(action="create_task", task_title=title, due_date=due)


# ---------------------------------------------------------------- duplicates

def test_duplicate_create_asks_instead_of_creating(monkeypatch):
    due = date.today() + timedelta(days=1)
    use_plan(monkeypatch, AgentPlan(actions=[create("play football", due)]))

    first = agent.process_request("add play football")
    assert not first.needs_clarification
    assert len(list_tasks()) == 1

    second = agent.process_request("add play football")
    assert second.needs_clarification
    assert "already exist" in second.message
    assert len(list_tasks()) == 1  # nothing was added


def test_duplicate_inside_one_plan_is_blocked(monkeypatch):
    due = date.today() + timedelta(days=1)
    use_plan(monkeypatch, AgentPlan(actions=[
        create("study", due), create("  STUDY ", due),
    ]))

    response = agent.process_request("add study twice")
    assert response.needs_clarification
    assert list_tasks() == []  # nothing ran


def test_same_title_different_date_is_allowed(monkeypatch):
    today = date.today()
    use_plan(monkeypatch, AgentPlan(actions=[
        create("gym", today + timedelta(days=1)),
        create("gym", today + timedelta(days=2)),
    ]))

    response = agent.process_request("add gym on two days")
    assert not response.needs_clarification
    assert len(list_tasks()) == 2


def tomorrow():
    return date.today() + timedelta(days=1)


def ask_duplicate(monkeypatch, titles=("play football",)):
    """Store 'play football', then ask for `titles` so the duplicate
    question comes back. Returns the history the CLI would build."""
    use_plan(monkeypatch, AgentPlan(
        actions=[create("play football", tomorrow())]))
    agent.process_request("add play football")
    use_plan(monkeypatch, AgentPlan(
        actions=[create(t, tomorrow()) for t in titles]))
    asked = agent.process_request("add them again")
    assert asked.needs_clarification
    return ["User: add them again", f"TaskPilot: {asked.message}"]


def test_reply_duplicate_adds_it_anyway(monkeypatch):
    history = ask_duplicate(monkeypatch)
    done = agent.process_request("duplicate", history)
    assert not done.needs_clarification
    assert len(list_tasks()) == 2


def test_reply_skip_adds_only_new_tasks(monkeypatch):
    history = ask_duplicate(monkeypatch, titles=("play football", "study"))
    done = agent.process_request("skip", history)
    assert [t.title for t in list_tasks()] == ["play football", "study"]
    assert "study" in done.message


def test_answer_runs_the_same_plan_without_the_llm(monkeypatch):
    history = ask_duplicate(monkeypatch)

    def boom(*a, **k):
        raise AssertionError("LLM must not be called")

    monkeypatch.setattr(agent, "interpret_request", boom)
    agent.process_request("duplicate", history)
    assert len(list_tasks()) == 2


def test_lost_plan_asks_to_resend(monkeypatch):
    history = ask_duplicate(monkeypatch)
    agent._pending_duplicates.clear()  # e.g. server restarted
    response = agent.process_request("duplicate", history)
    assert response.needs_clarification and "send it again" in response.message
    assert len(list_tasks()) == 1


def test_reply_skip_with_nothing_new(monkeypatch):
    history = ask_duplicate(monkeypatch)
    done = agent.process_request("skip", history)
    assert "nothing was added" in done.message
    assert len(list_tasks()) == 1


def test_unclear_reply_never_reaches_the_llm(monkeypatch):
    history = ask_duplicate(monkeypatch)

    def boom(*a, **k):
        raise AssertionError("LLM must not be called")

    monkeypatch.setattr(agent, "interpret_request", boom)
    again = agent.process_request("no dont update", history)
    assert again.needs_clarification and "skip" in again.message
    assert len(list_tasks()) == 1


def test_duplicate_answer_after_an_unclear_reply(monkeypatch):
    history = ask_duplicate(monkeypatch)
    history += ["User: hmm", history[1]]  # what the CLI builds
    done = agent.process_request("duplicate", history)
    assert not done.needs_clarification
    assert len(list_tasks()) == 2


def test_single_action_in_followup_not_pinned_to_last_weekday():
    d = date.today()
    sat = d + timedelta((5 - d.weekday()) % 7 or 7)
    plan = AgentPlan(actions=[create("x", sat)])
    text = "task on saturday and another on monday"
    assert agent._find_date_mismatch(plan, text, latest_only=True) == sat
    assert agent._find_date_mismatch(plan, text, latest_only=False) is None

# ------------------------------------------------------------- action limit

def test_schema_rejects_more_than_the_limit():
    too_many = [create(f"task {i}") for i in range(MAX_ACTIONS + 1)]
    with pytest.raises(ValidationError):
        AgentPlan(actions=too_many)


def test_plan_at_the_limit_runs_and_adds_a_note(monkeypatch):
    plan = AgentPlan(actions=[create(f"task {i}") for i in range(MAX_ACTIONS)])
    use_plan(monkeypatch, plan)

    response = agent.process_request("add lots of tasks")
    assert len(list_tasks()) == MAX_ACTIONS
    assert "the most I do per request" in response.message


def test_plan_below_the_limit_has_no_note(monkeypatch):
    plan = AgentPlan(actions=[create(f"task {i}")
                     for i in range(MAX_ACTIONS - 1)])
    use_plan(monkeypatch, plan)

    response = agent.process_request("add some tasks")
    assert len(list_tasks()) == MAX_ACTIONS - 1
    assert "the most I do per request" not in response.message

# ------------------------------------------------- weekday check exemptions


def test_tomorrow_task_alongside_a_weekday_task(monkeypatch):
    d = date.today()
    later = d + timedelta(days=3)
    use_plan(monkeypatch, AgentPlan(actions=[
        create("prepare", later), create("review", d + timedelta(days=1)),
    ]))
    response = agent.process_request(
        f"prepare by {later.strftime('%A')}, review tomorrow")
    assert not response.needs_clarification
    assert len(list_tasks()) == 2


def test_validate_exemptions_and_still_rejects_wrong_weekday():
    today = date(2026, 11, 13)  # a Friday
    text = "prepare by friday, review tomorrow, publish by monday"
    sat = date(2026, 11, 14)
    assert agent.validate_due_date(
        text, sat, False, today=today)      # tomorrow
    assert agent.validate_due_date(
        "do it today, publish monday", today, False, today=today)
    assert agent.validate_due_date(
        "publish by 2026-11-17, see monday", date(2026, 11, 17), False, today=today)
    # a date that is none of: named weekday, today, tomorrow, written date
    assert not agent.validate_due_date(
        text, date(2026, 11, 18), False, today=today)
    assert not agent.validate_due_date(
        "by friday", date(2026, 11, 16), today=today)
