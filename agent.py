from models import AgentDecision

from task_store import (
    create_task,
    update_task,
    delete_task,
    complete_task,
    list_tasks
)


def execute_decision(decision: AgentDecision):

    if decision.action == "create_task":

        if not decision.task_title:
            return "Task title is missing."

        return create_task(
            title=decision.task_title,
            due_date=decision.due_date
        )

    elif decision.action == "list_tasks":

        return list_tasks()

    elif decision.action == "update_task":

        if not decision.task_id:
            return "Task ID is missing."

        return update_task(
            task_id=decision.task_id,
            new_title=decision.new_title,
            new_due_date=decision.new_due_date
        )

    elif decision.action == "delete_task":

        if not decision.task_id:
            return "Task ID is missing."

        return delete_task(decision.task_id)

    elif decision.action == "complete_task":

        if not decision.task_id:
            return "Task ID is missing."

        return complete_task(decision.task_id)

    elif decision.action == "clarify":

        return decision.clarification
