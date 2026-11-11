
from datetime import date

from ollama import chat
from models import AgentDecision

MODEL = "qwen3:4b"

system_prompt = f"""
You are TaskPilot, an AI task management assistant.

Today's date is {date.today().isoformat()}.

Understand the user's task management request and decide
which action should be performed.

Convert relative dates into YYYY-MM-DD format.

If the request is ambiguous, choose the clarify action
and explain what information is missing.

Return only the structured data matching the provided schema.
"""

response = chat(
    model=MODEL,
    messages=[
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": "Remind me to finish my Python assignment tomorrow."
        }
    ],
    format=AgentDecision.model_json_schema()
)

if response.message.content is None:
    raise ValueError("The model returned an empty response.")

decision = AgentDecision.model_validate_json(
    response.message.content
)

print(decision)
print("\nAction:", decision.action)
print("Task:", decision.task_title)
print("Due date:", decision.due_date)
