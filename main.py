"""Interactive command-line interface for TaskPilot."""

from agent import AgentError, process_request
from models import AgentResponse
import logging
import os


def setup_logging() -> None:
    """Show log messages in the terminal. Set LOG_LEVEL=INFO to see more."""
    level = getattr(logging, os.getenv(
        "LOG_LEVEL", "WARNING").upper(), logging.WARNING)
    if not isinstance(level, int):
        level = logging.WARNING
    logging.basicConfig(
        level=level, format="%(levelname)s [%(name)s] %(message)s")


def format_response(response: AgentResponse) -> str:
    lines = [response.message]
    if response.action == "list_tasks":
        for task in response.tasks or []:
            mark = "x" if task.completed else " "
            due = f" (due {task.due_date})" if task.due_date else ""
            lines.append(f"  [{mark}] {task.title}{due}")
    return "\n".join(lines)


def main() -> None:
    setup_logging()
    print("TaskPilot - type 'exit' to quit, '/cancel' to drop a pending question.")
    history: list[str] | None = None

    while True:
        try:
            text = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not text:
            continue
        if text.lower() in ("exit", "quit"):
            break
        if text.lower() == "/cancel":
            print("\nTaskPilot:", "Clarification cancelled." if history
                  else "Nothing to cancel.")
            history = None
            continue

        try:
            response = process_request(text, history)
        except AgentError as exc:
            print("\nTaskPilot:", exc)
            continue

        if response.needs_clarification:
            history = (history or []) + [
                f"User: {text}",
                f"TaskPilot: {response.message}",
            ]
        else:
            history = None

        print("\nTaskPilot:", format_response(response))


if __name__ == "__main__":
    main()
