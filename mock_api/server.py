"""Mock API сервиса Task tracker (FastAPI, in-memory хранилище).

Домен: задачи. Операции:
    POST   /tasks          — создать задачу
    GET    /tasks/{id}     — получить задачу по id
    PATCH  /tasks/{id}     — обновить статус задачи
    GET    /tasks          — список задач (фильтр по статусу)
    GET    /stats          — статистика по задачам

Служебный эндпоинт (не операция домена):
    GET    /health         — проверка живости сервиса

Запуск: uvicorn mock_api.server:app --port 8000
"""

import itertools
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

Status = Literal["todo", "in_progress", "done"]

app = FastAPI(title="Task tracker mock API", version="1.0")

# in-memory хранилище: id -> задача
_TASKS: dict[int, dict] = {}
_IDS = itertools.count(1)


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, description="Название задачи")
    description: Optional[str] = Field(None, description="Описание задачи")


class StatusUpdate(BaseModel):
    status: Status = Field(..., description="Новый статус: todo | in_progress | done")


class Task(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: Status = "todo"


def _get_or_404(task_id: int) -> dict:
    task = _TASKS.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@app.get("/health")
def health() -> dict:
    """Служебный эндпоинт проверки живости сервиса (не операция домена)."""
    return {"status": "ok"}


@app.get("/")
def root() -> dict:
    return {"service": "Task tracker mock API", "operations": [
        "POST /tasks", "GET /tasks/{id}", "PATCH /tasks/{id}", "GET /tasks", "GET /stats",
    ]}


@app.post("/tasks", status_code=201)
def create_task(payload: TaskCreate) -> dict:
    task = {
        "id": next(_IDS),
        "title": payload.title,
        "description": payload.description,
        "status": "todo",
    }
    _TASKS[task["id"]] = task
    return task


@app.get("/tasks/{task_id}")
def get_task(task_id: int) -> dict:
    return _get_or_404(task_id)


@app.patch("/tasks/{task_id}")
def update_task_status(task_id: int, payload: StatusUpdate) -> dict:
    task = _get_or_404(task_id)
    task["status"] = payload.status
    return task


@app.get("/tasks")
def list_tasks(status: Optional[Status] = None) -> dict:
    tasks = [t for t in _TASKS.values() if status is None or t["status"] == status]
    return {"count": len(tasks), "tasks": tasks}


@app.get("/stats")
def stats() -> dict:
    by_status = {s: 0 for s in ("todo", "in_progress", "done")}
    for t in _TASKS.values():
        by_status[t["status"]] += 1
    return {"total": len(_TASKS), "by_status": by_status}
