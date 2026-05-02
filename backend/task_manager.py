"""Task manager — handles task lifecycle and delegation."""

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from .models import Task, TaskStatus

logger = logging.getLogger(__name__)


class TaskManager:
    """Manage tasks and task delegation."""

    def __init__(self):
        self.tasks: dict[str, dict] = {}

    def create_task(
        self,
        title: str,
        description: str,
        from_agent: str,
        to_agent: str,
        from_machine: str = None,
        to_machine: str = None,
    ) -> dict:
        """Create a new task and store it."""
        task_id = f"task-{int(time.time())}-{uuid.uuid4().hex[:4]}"
        now = time.time()
        task = {
            "task_id": task_id,
            "title": title,
            "description": description,
            "from_agent": from_agent,
            "to_agent": to_agent,
            "from_machine": from_machine,
            "to_machine": to_machine,
            "status": "PENDING",
            "result": None,
            "created_at": now,
            "updated_at": now,
        }
        self.tasks[task_id] = task
        logger.info("Task created: %s -> %s (%s)", from_agent, to_agent, task_id)
        return task

    def get_task(self, task_id: str) -> Optional[dict]:
        """Get a task by id."""
        return self.tasks.get(task_id)

    def get_pending_tasks(self, agent_id: str) -> list[dict]:
        """Get pending tasks for an agent."""
        return [
            t for t in self.tasks.values()
            if t.get("to_agent") == agent_id and t.get("status") == "PENDING"
        ]

    def get_tasks_by_from_agent(self, from_agent: str) -> list[dict]:
        """Get tasks created by an agent."""
        return [t for t in self.tasks.values() if t.get("from_agent") == from_agent]

    def list_all(self, from_agent: str = None, to_agent: str = None) -> list[dict]:
        """List tasks, optionally filtered by source or target agent."""
        results = list(self.tasks.values())
        if from_agent:
            results = [t for t in results if t.get("from_agent") == from_agent]
        if to_agent:
            results = [t for t in results if t.get("to_agent") == to_agent]
        return sorted(results, key=lambda t: t.get("created_at", 0), reverse=True)

    def update_task(self, task_id: str, status: str, result: str = None) -> Optional[dict]:
        """Update task status and optionally set result."""
        task = self.tasks.get(task_id)
        if task:
            task["status"] = status
            if result is not None:
                task["result"] = result
            task["updated_at"] = time.time()
            logger.info("Task %s -> %s", task_id, status)
        return task

    async def delegate_task(
        self,
        from_agent: str,
        from_machine: str,
        to_project: str,
        title: str,
        description: str,
    ) -> dict:
        """Delegate task to target project."""
        from .agent_registry import agent_registry
        from .websocket_handler import proxy_manager

        candidates = agent_registry.find_by_project(to_project)

        if not candidates:
            logger.warning("No agents found for project: %s", to_project)
            return {"type": "delegate_failed", "error": f"No agent in project {to_project}"}

        # Filter out offline agents
        candidates = [a for a in candidates if a.get("status") != "OFFLINE"]

        if not candidates:
            logger.warning("All agents offline for project: %s", to_project)
            return {"type": "delegate_failed", "error": f"All agents offline in project {to_project}"}

        # Prefer idle agents
        idle = [a for a in candidates if a.get("status") == "IDLE"]
        target_agent = idle[0] if idle else candidates[0]

        # Create task
        task_id = f"task-{int(time.time())}-{uuid.uuid4().hex[:4]}"
        now = time.time()
        task = {
            "task_id": task_id,
            "from_agent": from_agent,
            "from_machine": from_machine,
            "to_agent": target_agent.get("agent_id"),
            "to_machine": target_agent.get("machine_ip"),
            "title": title,
            "description": description,
            "status": "PENDING",
            "created_at": now,
            "updated_at": now,
        }
        self.tasks[task_id] = task

        logger.info(
            "Task %s delegated: %s -> %s (project=%s)",
            task_id, from_agent, target_agent.get("agent_id"), to_project
        )

        # Notify target machine
        await proxy_manager.send_to_machine(target_agent.get("machine_ip"), {
            "type": "task_assigned",
            "agent_id": target_agent.get("agent_id"),
            "task": task,
        })

        return {
            "type": "delegate_success",
            "task_id": task_id,
            "target_agent": target_agent.get("agent_id"),
        }


# Global instance
task_manager = TaskManager()


# Module-level function aliases for backward compatibility with Pydantic models
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


def update_task_status(task_id: str, status: TaskStatus, result: Optional[str] = None) -> Optional[Task]:
    """Update task status and optionally set result."""
    task = _tasks.get(task_id)
    if task:
        task.status = status
        if result is not None:
            task.result = result
        task.updated_at = datetime.now(timezone.utc)
        logger.info("Task %s -> %s", task_id, status.value)
    return task