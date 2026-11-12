from fastapi import FastAPI, HTTPException, Response
from task_store import list_tasks, create_task, update_task, delete_task
from models import TaskCreate, TaskUpdate, AgentRequest
from agent import process_request

app = FastAPI(
    title="TaskPilot API",
    description="AI-powered task management API",
    version="1.0.0"
)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/api/tasks")
def get_tasks():
    return list_tasks()


@app.post("/api/tasks", status_code=201)
def post_task(task: TaskCreate):
    return create_task(
        title=task.title,
        due_date=task.due_date
    )


@app.patch("/api/tasks/{task_id}")
def patch_task(task_id: str, task: TaskUpdate):
    updated_task = update_task(
        task_id=task_id,
        new_title=task.title,
        new_due_date=task.due_date,
        new_completed=task.completed
    )

    if updated_task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    return updated_task


@app.delete("/api/tasks/{task_id}", status_code=204)
def remove_task(task_id: str):
    deleted = delete_task(task_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    return Response(status_code=204)


@app.post("/api/agent/execute")
def execute_agent(request: AgentRequest):
    return process_request(request.user_request)
