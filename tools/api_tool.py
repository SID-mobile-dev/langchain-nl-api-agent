"""LangChain tool для вызова API Task tracker.

Один tool с параметром operation покрывает все операции mock API:
    create_task         — POST   /tasks
    get_task            — GET    /tasks/{task_id}
    update_task_status  — PATCH  /tasks/{task_id}
    list_tasks          — GET    /tasks
    stats               — GET    /stats

Внутри — реальный HTTP-вызов (httpx) к API_BASE_URL.
Возвращает структурированный результат (dict -> JSON -> string):

    {
      "ok": true|false,
      "operation": "<operation>",
      "action": "<метод и путь HTTP>",
      "http_status": <код ответа или null>,
      "data": <тело ответа API или null>,
      "errors": ["..."]   # пусто, если ok=true
    }

Каждый вызов и результат логируются в консоль (logger "api_tool").
"""

import json
import logging
import os
from typing import Literal, Optional

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field

Operation = Literal["create_task", "get_task", "update_task_status", "list_tasks", "stats"]
TaskStatus = Literal["todo", "in_progress", "done"]

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
TIMEOUT_SECONDS = 10.0

logger = logging.getLogger("api_tool")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[api_tool] %(levelname)s %(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)


class ApiToolArgs(BaseModel):
    """Схема аргументов tool: operation + параметры операций."""

    operation: Operation = Field(
        ...,
        description=(
            "Операция API Task tracker: create_task (создать задачу), "
            "get_task (получить по id), update_task_status (обновить статус), "
            "list_tasks (список, фильтр по статусу), stats (статистика)."
        ),
    )
    task_id: Optional[int] = Field(
        None, description="Id задачи. Обязателен для get_task и update_task_status."
    )
    title: Optional[str] = Field(
        None, description="Название задачи. Обязательно для create_task."
    )
    description: Optional[str] = Field(
        None, description="Описание задачи. Необязательно для create_task."
    )
    status: Optional[TaskStatus] = Field(
        None,
        description=(
            "Статус задачи: todo | in_progress | done. "
            "Обязателен для update_task_status, необязателен (фильтр) для list_tasks."
        ),
    )


def _result(operation: str, action: str, http_status: Optional[int],
            data: Optional[dict], errors: list) -> dict:
    return {
        "ok": not errors,
        "operation": operation,
        "action": action,
        "http_status": http_status,
        "data": data,
        "errors": errors,
    }


def call_api(operation: str, task_id: Optional[int] = None, title: Optional[str] = None,
             description: Optional[str] = None, status: Optional[str] = None) -> dict:
    """Выполнить операцию API реальным HTTP-вызовом и вернуть структурированный результат."""
    base_url = os.environ.get("API_BASE_URL", DEFAULT_API_BASE_URL).rstrip("/")

    if operation == "create_task":
        method, path = "POST", "/tasks"
        payload = {"title": title, "description": description}
        params = None
        if not title:
            return _result(operation, f"{method} {path}", None, None,
                           ["title is required for create_task"])
    elif operation == "get_task":
        method, path = "GET", f"/tasks/{task_id}"
        payload, params = None, None
        if task_id is None:
            return _result(operation, "GET /tasks/{task_id}", None, None,
                           ["task_id is required for get_task"])
    elif operation == "update_task_status":
        method, path = "PATCH", f"/tasks/{task_id}"
        payload, params = {"status": status}, None
        if task_id is None or not status:
            return _result(operation, "PATCH /tasks/{task_id}", None, None,
                           ["task_id and status are required for update_task_status"])
    elif operation == "list_tasks":
        method, path = "GET", "/tasks"
        payload = None
        params = {"status": status} if status else None
    elif operation == "stats":
        method, path = "GET", "/stats"
        payload, params = None, None
    else:
        return _result(operation, "", None, None, [f"Unknown operation: {operation}"])

    url = f"{base_url}{path}"
    logger.info("-> %s %s params=%s payload=%s", method, url, params, payload)
    try:
        response = httpx.request(method, url, params=params, json=payload, timeout=TIMEOUT_SECONDS)
    except httpx.HTTPError as exc:
        logger.info("<- %s FAILED: %s", operation, exc)
        return _result(operation, f"{method} {path}", None, None,
                       [f"Connection error: {exc.__class__.__name__}: {exc}"])

    try:
        data = response.json()
    except ValueError:
        data = {"raw": response.text}

    logger.info("<- %s HTTP %s data=%s", operation, response.status_code, data)
    if response.is_success:
        return _result(operation, f"{method} {path}", response.status_code, data, [])
    return _result(operation, f"{method} {path}", response.status_code, None,
                   [f"HTTP {response.status_code}: {json.dumps(data, ensure_ascii=False)}"])


@tool("api_tool", args_schema=ApiToolArgs)
def api_tool(operation: str, task_id: Optional[int] = None, title: Optional[str] = None,
             description: Optional[str] = None, status: Optional[str] = None) -> str:
    """Вызвать операцию API Task tracker и вернуть структурированный результат (JSON-строкой).

    Используй этот tool для любых действий с задачами: создания, получения,
    обновления статуса, получения списка или статистики. Данные бери только
    из результата tool — не выдумывай их.
    """
    result = call_api(operation, task_id=task_id, title=title,
                      description=description, status=status)
    return json.dumps(result, ensure_ascii=False)
