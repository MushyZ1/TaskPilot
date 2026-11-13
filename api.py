"""TaskPilot HTTP API."""

import logging

from fastapi import FastAPI, HTTPException, Response

from agent import AgentError, process_request
from models import AgentRequest, AgentResponse, Task, TaskCreate, TaskUpdate
from task_store import (
    create_task,
    delete_task,
    get_task,
    list_tasks,
    update_task,
)

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="TaskPilot API",
    description="AI-powered task management API",
    version="1.0.0",
)


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Task not found")


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/api/tasks", response_model=list[Task])
def get_tasks():
    return list_tasks()


@app.get("/api/tasks/{task_id}", response_model=Task)
def read_task(task_id: str):
    task = get_task(task_id)
    if task is None:
        raise _not_found()
    return task


@app.post("/api/tasks", status_code=201, response_model=Task)
def post_task(task: TaskCreate):
    return create_task(title=task.title, due_date=task.due_date)


@app.patch("/api/tasks/{task_id}", response_model=Task)
def patch_task(task_id: str, task: TaskUpdate):
    if not task.model_fields_set:
        raise HTTPException(
            status_code=400, detail="Provide at least one field to update"
        )

    updated = update_task(
        task_id=task_id,
        new_title=task.title,
        new_due_date=task.due_date,
        new_completed=task.completed,
    )
    if updated is None:
        raise _not_found()
    return updated


@app.delete("/api/tasks/{task_id}", status_code=204)
def remove_task(task_id: str):
    if not delete_task(task_id):
        raise _not_found()
    return Response(status_code=204)


@app.post("/api/agent/execute", response_model=AgentResponse)
def execute_agent(request: AgentRequest):
    try:
        return process_request(request.user_request, request.history)
    except AgentError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
