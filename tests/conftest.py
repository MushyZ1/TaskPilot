import json
from datetime import date, timedelta
from typing import Any

import pytest

import agent
import task_store


class FakeLLM:
    """Returns queued plans instead of calling a real model."""

    def __init__(self):
        self.queue = []
        self.calls = []

    def add(self, **decision):
        """Queue a plan containing a single action."""
        self.queue.append({"actions": [decision]})

    def add_plan(self, *decisions, note=None):
        """Queue a plan containing several actions."""
        plan: dict[str, Any] = {"actions": list(decisions)}
        if note:
            plan["note"] = note
        self.queue.append(plan)

    def generate(self, messages, response_format):
        self.calls.append(messages)
        item = self.queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item if isinstance(item, str) else json.dumps(item)


@pytest.fixture(autouse=True)
def clean_state():
    task_store.reset_tasks()
    agent._provider = None
    yield
    task_store.reset_tasks()
    agent._provider = None


@pytest.fixture
def llm():
    fake = FakeLLM()
    agent._provider = fake
    return fake


def next_weekday(name: str) -> date:
    """Date of the next occurrence (1-7 days ahead) of a weekday."""
    for i in range(1, 8):
        d = date.today() + timedelta(days=i)
        if d.strftime("%A").lower() == name:
            return d
    raise ValueError(f"Unknown weekday: {name!r}")
