from agent import process_request


pending_context = None


while True:

    user_request = input("\nYou: ").strip()

    if user_request.lower() in ["exit", "quit"]:
        break

    # Allow the user to cancel a pending clarification.
    if user_request.lower() == "/cancel":

        if pending_context is not None:
            pending_context = None
            print("\nTaskPilot: Clarification cancelled.")

        else:
            print("\nTaskPilot: Nothing to cancel.")

        continue

    # No clarification is currently pending.
    if pending_context is None:

        result, needs_clarification = process_request(user_request)

        if needs_clarification:

            pending_context = [
                f"User: {user_request}",
                f"TaskPilot: {result}"
            ]

    # We are waiting for the user's clarification.
    else:

        pending_context.append(f"User: {user_request}")

        result, needs_clarification = process_request(
            user_request,
            conversation_context=pending_context
        )

        if needs_clarification:

            pending_context.append(f"TaskPilot: {result}")

        else:

            pending_context = None

    print("\nTaskPilot:", result)
