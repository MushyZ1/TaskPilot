from typing import Literal
from pydantic import BaseModel, Field
from datetime import date


from datetime import date
from typing import Literal
from pydantic import BaseModel


class AgentDecision(BaseModel):
    action: Literal[
        "create_task",
        "update_task",
        "delete_task",
        "list_tasks",
        "complete_task",
        "clarify"
    ]

    task_id: str | None = None
    task_title: str | None = None
    new_title: str | None = None

    due_date: date | None = None
    new_due_date: date | None = None

    clarification: str | None = None


class Task(BaseModel):
    id: str
    title: str
    due_date: date | None = None
    completed: bool = False


class TaskCreate(BaseModel):
    title: str
    due_date: date | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    due_date: date | None = None
    completed: bool | None = None

class AgentRequest(BaseModel):
    user_request: str