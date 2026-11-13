from datetime import date

import pytest

import task_store as store


def test_create_and_list():
    task = store.create_task("  Buy milk ", date(2030, 1, 1))
    assert task.title == "Buy milk"
    assert task.completed is False
    assert [t.id for t in store.list_tasks()] == [task.id]


def test_blank_title_rejected():
    with pytest.raises(ValueError):
        store.create_task("   ")


def test_update_fields_independently():
    task = store.create_task("A", date(2030, 1, 1))

    updated = store.update_task(task.id, new_title="B")
    assert updated is not None
    assert (updated.title, updated.due_date) == ("B", date(2030, 1, 1))

    updated = store.update_task(task.id, new_completed=True)
    assert updated is not None
    assert updated.completed is True


def test_update_missing_returns_none():
    assert store.update_task("nope", new_title="x") is None


def test_complete_and_delete():
    task = store.create_task("A")

    completed = store.complete_task(task.id)
    assert completed is not None
    assert completed.completed is True
    assert store.complete_task("nope") is None

    assert store.delete_task(task.id) is True
    assert store.delete_task(task.id) is False
    assert store.list_tasks() == []


def test_returned_tasks_are_copies():
    task = store.create_task("A")
    task.title = "mutated"
    store.list_tasks()[0].title = "mutated"

    stored = store.get_task(task.id)
    assert stored is not None
    assert stored.title == "A"
