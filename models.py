from typing import Literal
from pydantic import BaseModel, Field


class AgentDecision(BaseModel):
    action: Literal[
        "create_task",
        "update_task",
        "delete_task",
        "list_tasks",
        "complete_task",
        "clarify"
    ]

    task_title: str | None = None
    due_date: str | None = None
    clarification: str | None = None
