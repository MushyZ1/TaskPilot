"""Thread-safe in-memory task storage.

Data lives only for the lifetime of the process. Swap this module for a
database-backed implementation to persist tasks.
"""

import threading
from datetime import date
from uuid import uuid4

from models import Task

_lock = threading.RLock()
_tasks: dict[str, Task] = {}  # dicts keep insertion order


def create_task(title: str, due_date: date | None = None) -> Task:
    title = title.strip()
    if not title:
        raise ValueError("Task title must not be blank")

    task = Task(id=str(uuid4()), title=title, due_date=due_date)
    with _lock:
        _tasks[task.id] = task
        return task.model_copy()


def get_task(task_id: str) -> Task | None:
    with _lock:
        task = _tasks.get(task_id)
        return task.model_copy() if task else None


def update_task(
    task_id: str,
    new_title: str | None = None,
    new_due_date: date | None = None,
    new_completed: bool | None = None,
) -> Task | None:
    """Update the given fields. Returns the task, or None if not found."""
    if new_title is not None:
        new_title = new_title.strip()
        if not new_title:
            raise ValueError("Task title must not be blank")

    with _lock:
        task = _tasks.get(task_id)
        if task is None:
            return None
        if new_title is not None:
            task.title = new_title
        if new_due_date is not None:
            task.due_date = new_due_date
        if new_completed is not None:
            task.completed = new_completed
        return task.model_copy()


def complete_task(task_id: str) -> Task | None:
    return update_task(task_id, new_completed=True)


def delete_task(task_id: str) -> bool:
    with _lock:
        return _tasks.pop(task_id, None) is not None


def list_tasks() -> list[Task]:
    """Return copies, so callers cannot mutate stored tasks."""
    with _lock:
        return [task.model_copy() for task in _tasks.values()]


def reset_tasks() -> None:
    """Remove every task (used by tests)."""
    with _lock:
        _tasks.clear()
