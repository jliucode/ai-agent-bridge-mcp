"""REST API routes for the AI Agent Bridge."""

from fastapi import APIRouter

from .agent_registry import get, list_all
from .task_manager import get as get_task, list_all as list_tasks

router = APIRouter()


@router.get("/api/agents")
async def api_list_agents():
    agents = [a.model_dump(mode="json") for a in list_all()]
    return {"agents": agents, "count": len(agents)}


@router.get("/api/agents/{agent_id}")
async def api_get_agent(agent_id: str):
    agent = get(agent_id)
    if not agent:
        return {"error": "Agent not found"}, 404
    return agent.model_dump(mode="json")


@router.get("/api/tasks")
async def api_list_tasks(from_agent: str = None, to_agent: str = None):
    tasks = [t.model_dump(mode="json") for t in list_tasks(from_agent=from_agent, to_agent=to_agent)]
    return {"tasks": tasks, "count": len(tasks)}


@router.get("/api/tasks/{task_id}")
async def api_get_task(task_id: str):
    task = get_task(task_id)
    if not task:
        return {"error": "Task not found"}, 404
    return task.model_dump(mode="json")


@router.get("/api/stats")
async def api_stats():
    agents = list_all()
    tasks = list_tasks()
    online = sum(1 for a in agents if a.status.value in ("ONLINE", "BUSY", "IDLE"))
    return {
        "total_agents": len(agents),
        "online_agents": online,
        "offline_agents": len(agents) - online,
        "busy_agents": sum(1 for a in agents if a.status.value == "BUSY"),
        "total_tasks": len(tasks),
        "pending_tasks": sum(1 for t in tasks if t.status.value == "PENDING"),
        "in_progress_tasks": sum(1 for t in tasks if t.status.value == "IN_PROGRESS"),
        "completed_tasks": sum(1 for t in tasks if t.status.value == "DONE"),
        "failed_tasks": sum(1 for t in tasks if t.status.value == "FAILED"),
    }


@router.get("/health")
async def health_check():
    return {"status": "ok"}
