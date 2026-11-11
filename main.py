from ollama import chat

MODEL = "qwen3:4b"

response = chat(
    model=MODEL,
    messages=[
        {
            "role": "system",
            "content": "You are TaskPilot, an AI task management assistant. You help users create, update, delete, and organise tasks. Be concise and ask for clarification when a request is ambiguous."
        },
        {
            "role": "user",
            "content": "Remind me to finish my Python assignment tomorrow."
        }
    ]
)

print(response.message.content)
