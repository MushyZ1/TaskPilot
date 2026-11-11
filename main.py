from datetime import date

from task_store import (
    create_task,
    update_task,
    delete_task,
    complete_task,
    list_tasks
)

# 1. Create two tasks
task1 = create_task(
    "Finish Python assignment",
    date(2026, 11, 12)
)

task2 = create_task("Learn FastAPI")

print("\n--- CREATED TASKS ---")
print(list_tasks())


# 2. Update the first task
updated = update_task(
    task_id=task1.id,
    new_title="Finish TaskPilot assignment"
)

print("\n--- UPDATED TASK ---")
print(updated)


# 3. Complete the first task
completed = complete_task(task1.id)

print("\n--- COMPLETED TASK ---")
print(completed)


# 4. Delete the second task
deleted = delete_task(task2.id)

print("\n--- DELETION RESULT ---")
print(deleted)

# Try updating a task that doesn't exist
print(update_task("invalid-id", new_title="Test"))

# Try deleting a task that doesn't exist
print(delete_task("invalid-id"))

# Try completing a task that doesn't exist
print(complete_task("invalid-id"))

# Try setting completed back to False
print(update_task(task1.id, new_completed=False))


# 5. List remaining tasks
print("\n--- REMAINING TASKS ---")
for task in list_tasks():
    print(task)
