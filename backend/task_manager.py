"""Task manager — handles task lifecycle and delegation."""

import logging
from datetime import datetime, timezone
from typing import Optional

from .models import Task, TaskStatus

logger = logging.getLogger(__name__)

_tasks: dict[str, Task] = {}


def create_task(title: str, description: str, from_agent: str, to_agent: str) -> Task:
    """Create a new task and store it."""
    task = Task(
        title=title,
        description=description,
        from_agent=from_agent,
        to_agent=to_agent,
    )
    _tasks[task.id] = task
    logger.info("Task created: %s -> %s (%s)", from_agent, to_agent, task.id)
    return task


def get(task_id: str) -> Optional[Task]:
    """Get a task by id."""
    return _tasks.get(task_id)


def list_all(from_agent: Optional[str] = None, to_agent: Optional[str] = None) -> list[Task]:
    """List tasks, optionally filtered by source or target agent."""
    results = list(_tasks.values())
    if from_agent:
        results = [t for t in results if t.from_agent == from_agent]
    if to_agent:
        results = [t for t in results if t.to_agent == to_agent]
    return sorted(results, key=lambda t: t.created_at, reverse=True)


def update_task(task_id: str, status: TaskStatus, result: Optional[str] = None) -> Optional[Task]:
    """Update task status and optionally set result."""
    task = _tasks.get(task_id)
    if task:
        task.status = status
        if result is not None:
            task.result = result
        task.updated_at = datetime.now(timezone.utc)
        logger.info("Task %s -> %s", task_id, status.value)
    return task
