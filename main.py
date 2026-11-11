from agent import process_request


while True:

    user_request = input("\nYou: ")

    if user_request.lower() in ["exit", "quit"]:
        break

    result = process_request(user_request)

    print("\nTaskPilot:", result)
