"""Pydantic models shared by the agent, the task store and the API."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

MAX_ACTIONS = 15  # most actions the agent will run for one request

def _clean_title(value: str | None) -> str | None:
    """Strip whitespace and reject titles that are blank."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        raise ValueError("title must not be blank")
    return value


class AgentDecision(BaseModel):
    """Structured output the LLM must return."""

    action: Literal[
        "create_task",
        "update_task",
        "delete_task",
        "list_tasks",
        "complete_task",
        "clarify",
    ]

    task_id: str | None = None
    task_title: str | None = None
    new_title: str | None = None

    due_date: date | None = None
    new_due_date: date | None = None

    clarification: str | None = None


class AgentPlan(BaseModel):
    """What the LLM returns: one or more actions, executed in order."""

    actions: list[AgentDecision] = Field(min_length=1, max_length=MAX_ACTIONS)
    # Anything the model could not do or chose to ignore, shown to the user.
    note: str | None = None

class Task(BaseModel):
    id: str
    title: str
    due_date: date | None = None
    completed: bool = False


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    due_date: date | None = None

    _strip_title = field_validator("title")(_clean_title)


class TaskUpdate(BaseModel):
    """Partial update. Fields left as ``None`` are not changed."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    due_date: date | None = None
    completed: bool | None = None

    _strip_title = field_validator("title")(_clean_title)


class AgentRequest(BaseModel):
    user_request: str = Field(min_length=1, max_length=1000)
    history: list[str] | None = Field(default=None, max_length=20)

    @field_validator("user_request")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("user_request must not be blank")
        return value


class AgentResponse(BaseModel):
    """What the agent (and the /api/agent/execute endpoint) returns."""

    message: str
    needs_clarification: bool = False
    action: str | None = None
    task: Task | None = None
    tasks: list[Task] | None = None
