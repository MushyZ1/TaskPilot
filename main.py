from datetime import date

from models import AgentDecision
from agent import execute_decision


decision = AgentDecision(
    action="create_task",
    task_title="Finish Python assignment",
    due_date=date(2026, 11, 12)
)

result = execute_decision(decision)

print("Agent result:", result)


decision = AgentDecision(
    action="list_tasks"
)

result = execute_decision(decision)

print("\nAll tasks:", result)
