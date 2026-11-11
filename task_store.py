from uuid import uuid4
from datetime import date

from models import Task

tasks: list[Task] = []


def create_task(title: str, due_date: date | None = None):
    task = Task(
        id=str(uuid4()),
        title=title,
        due_date=due_date
    )

    tasks.append(task)

    return task


def update_task(
    task_id: str,
    new_title: str | None = None,
    new_due_date: date | None = None,
    new_completed: bool | None = None
):
    for task in tasks:
        if task.id == task_id:

            if new_title is not None:
                task.title = new_title

            if new_due_date is not None:
                task.due_date = new_due_date

            if new_completed is not None:
                task.completed = new_completed

            return task

    return None


def delete_task(task_id: str):
    for task in tasks:
        if task.id == task_id:
            tasks.remove(task)
            return True

    return False


def complete_task(task_id: str):
    for task in tasks:
        if task.id == task_id:
            task.completed = True
            return task

    return None

def list_tasks():
    return tasks
