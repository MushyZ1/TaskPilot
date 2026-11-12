from models import AgentDecision
import json
from datetime import date, timedelta
from llm_provider import get_provider
import re
import time


from task_store import (
    create_task,
    update_task,
    delete_task,
    complete_task,
    list_tasks
)

MODEL = "qwen3:4b"

provider = get_provider()


def validate_due_date(user_request: str, proposed_date: date | None):

    if proposed_date is None:
        return True

    weekdays = [
        "monday", "tuesday", "wednesday",
        "thursday", "friday", "saturday", "sunday"
    ]

    # Find weekday mentions in the order they appear.
    mentioned_weekdays = re.findall(
        r"\b(" + "|".join(weekdays) + r")\b",
        user_request.lower()
    )

    # If no weekday was mentioned, there is nothing to check.
    if not mentioned_weekdays:
        return True

    # Use the most recently mentioned weekday.
    expected_weekday = mentioned_weekdays[-1]

    return proposed_date.strftime("%A").lower() == expected_weekday


def get_validation_text(
    user_request: str,
    conversation_context: list[str] | None
):
    if not conversation_context:
        return user_request

    user_messages = [
        message.removeprefix("User: ")
        for message in conversation_context
        if message.startswith("User: ")
    ]

    return "\n".join(user_messages)


def interpret_request(user_request: str, date_feedback: str | None = None, conversation_context: list[str] | None = None):

    existing_tasks = [
        task.model_dump(mode="json")
        for task in list_tasks()
    ]

    today = date.today()


    upcoming_dates = {
        (today + timedelta(days=i)).strftime("%A"):
        (today + timedelta(days=i)).isoformat()
        for i in range(1, 8)
    }

    system_prompt = f"""
    You are TaskPilot, an AI task management assistant.

    Today's date is {date.today().isoformat()}.

    Upcoming weekday dates:
    {json.dumps(upcoming_dates, indent=2)}

    The user's existing tasks are:
    {json.dumps(existing_tasks, indent=2)}

    Understand the user's request and select the appropriate action.

    Available actions:
    - create_task
    - update_task
    - delete_task
    - list_tasks
    - complete_task
    - clarify

    Rules:
    1. For create_task:
       - task_title is REQUIRED.
       - Extract the task name from the user's request.
       - due_date should contain the requested due date.
       - new_title and new_due_date must be null.
       - clarification must be null.

    2. For update_task:
       - task_id is REQUIRED.
       - Only populate new_title or new_due_date if requested.
       - task_title must be null.

    3. For delete_task and complete_task:
       - task_id is REQUIRED.
       - Identify the task using the existing task list.
       - Never invent a task ID.

    4. For list_tasks:
       - All task properties must be null.

    5. For clarify:
       - Explain what information is missing in clarification.
       - All other properties must be null.

    6. Convert relative dates into YYYY-MM-DD format.
    7. If multiple tasks could match, ask for clarification.
    8. Never invent task information.
    9. Return structured data matching the provided schema.
    10. If the user explicitly asks to create, add, or make a task,
    choose create_task.

    11. Never silently convert a create request into an update.

    12. If an identical task already exists and the user requests
        another one, ask whether they want a duplicate or an update.

    13. When a user mentions a weekday, use the corresponding
        date from the upcoming weekday dates provided above.
        Never calculate weekday dates yourself.
    """

    if date_feedback:
        system_prompt += f"""

        IMPORTANT CORRECTION:
        {date_feedback}

        Reconsider your date interpretation carefully.
        Return a corrected decision using the required schema.
        """

    if conversation_context:
        user_message = "\n".join(conversation_context)

        user_message += """

        This is an ongoing conversation.
        Interpret the latest user message in the context
        of the original request and previous clarification.

        Do not treat the latest message as an unrelated request.
        Resolve the original request using the clarification.
        """
    else:
        user_message = user_request

    start_time = time.perf_counter()

    content = provider.generate(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        response_format=AgentDecision.model_json_schema()
    )

    end_time = time.perf_counter()


    print(f"LLM response time: {end_time - start_time:.2f} seconds")

    decision = AgentDecision.model_validate_json(content)

    return decision


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


def process_request(
    user_request: str,
    conversation_context: list[str] | None = None
):

    decision = interpret_request(
        user_request,
        conversation_context=conversation_context
    )

    # If the LLM needs clarification, return immediately.
    if decision.action == "clarify":
        return decision.clarification, True

    # Get the date proposed by the LLM.
    if decision.action == "create_task":
        proposed_date = decision.due_date

    elif decision.action == "update_task":
        proposed_date = decision.new_due_date

    else:
        proposed_date = None

    # Include previous user messages when validating dates.
    validation_text = get_validation_text(
        user_request,
        conversation_context
    )

    # Validate the proposed date.
    if not validate_due_date(validation_text, proposed_date):

        print("\nIncorrect date interpretation. Retrying...")

        decision = interpret_request(
            user_request,
            date_feedback=(
                f"You previously returned {proposed_date}, "
                f"but the user's requested weekday does not match. "
                f"Reconsider the date using today's date: "
                f"{date.today().isoformat()}."
            ),
            conversation_context=conversation_context
        )

        # The retry might itself require clarification.
        if decision.action == "clarify":
            return decision.clarification, True

        # Get the date from the retry.
        if decision.action == "create_task":
            proposed_date = decision.due_date

        elif decision.action == "update_task":
            proposed_date = decision.new_due_date

        else:
            proposed_date = None

        # Validate the retry.
        if not validate_due_date(validation_text, proposed_date):
            return (
                "I'm unable to confidently determine the correct date. "
                "Could you clarify?",
                True
            )

    print("\nAgent decision:", decision)

    return execute_decision(decision), False


