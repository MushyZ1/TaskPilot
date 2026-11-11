import pytest
from task_store import (
    create_task,
    update_task,
    delete_task,
    complete_task,
    list_tasks
)
from models import Task
from datetime import date


@pytest.fixture(autouse=True)
def clean_tasks():
    list_tasks().clear()

def test_create_task():
    task = create_task(title="Python Task")

    assert task.title == "Python Task"
    assert task.completed is False
    assert task.due_date is None
    assert task.id is not None


def test_create_task_adds_to_list():
    task = create_task(title="Python Task")

    assert task in list_tasks()
    assert len(list_tasks()) == 1


def test_update_task_title():
    task = create_task(title="Learn Python")

    updated_task = update_task(
        task_id=task.id,
        new_title="Learn Java"
    )

    assert updated_task is not None
    assert updated_task.title == "Learn Java"
    assert task.title == "Learn Java"


def test_update_task_due_date():
    task = create_task(title="Study AI")

    new_due_date = date(2026, 11, 20)

    updated_task = update_task(
        task_id=task.id,
        new_due_date=new_due_date
    )

    assert updated_task is not None
    assert updated_task.due_date == new_due_date
    assert task.due_date == new_due_date


def test_update_task_completion():
    task = create_task(title="Learn Python")

    updated_task = update_task(
        task_id=task.id,
        new_completed=True
    )

    assert updated_task is not None
    assert updated_task.completed is True
    assert task.completed is True


def test_update_nonexistent_task():
    updated_task = update_task(
        task_id="invalid-id",
        new_title="New title"
    )

    assert updated_task is None


def test_delete_task():
    task = create_task(title="Learn Python")

    result = delete_task(task.id)

    assert result is True
    assert task not in list_tasks()
    assert len(list_tasks()) == 0


def test_delete_nonexistent_task():
    result = delete_task("invalid-id")

    assert result is False


def test_complete_task():
    task = create_task(title="Finish project")

    completed_task = complete_task(task.id)

    assert completed_task is not None
    assert completed_task.completed is True
    assert task.completed is True


def test_complete_nonexistent_task():
    completed_task = complete_task("invalid-id")

    assert completed_task is None


def test_list_tasks():
    task1 = create_task(title="Learn Python")
    task2 = create_task(title="Learn FastAPI")

    result = list_tasks()

    assert len(result) == 2
    assert task1 in result
    assert task2 in result


def test_list_tasks_empty():
    result = list_tasks()

    assert result == []
    assert len(result) == 0
