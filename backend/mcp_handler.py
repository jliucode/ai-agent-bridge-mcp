"""MCP JSON-RPC 2.0 handler over SSE transport."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import Request
from fastapi.responses import StreamingResponse

from .agent_registry import (
    get,
    list_all,
    register,
    unregister,
    update_current_task,
    update_heartbeat,
    update_status,
)
from .models import (
    Agent,
    AgentCapability,
    AgentRegisterRequest,
    AgentStatus,
    TaskDelegateRequest,
    TaskStatus,
    TaskUpdateRequest,
)
from .task_manager import create_task, get as get_task, list_all as list_tasks, update_task

logger = logging.getLogger(__name__)

# SSE channels: session_id -> asyncio.Queue
_sse_channels: dict[str, asyncio.Queue] = {}

# session_id -> agent_id mapping
_session_agents: dict[str, str] = {}

# Topics for frontend WebSocket
_frontend_subscribers: list[asyncio.Queue] = []


def _new_session_id():
    return uuid4().hex


async def broadcast_event(event_type: str, data: dict):
    """Push an event to all frontend WebSocket subscribers."""
    payload = json.dumps({"type": event_type, "data": data}, default=str)
    for queue in _frontend_subscribers[:]:
        try:
            await queue.put(payload)
        except Exception:
            _frontend_subscribers.remove(queue)


async def _push_to_agent(agent_id: str, event_type: str, data: dict):
    """Push an SSE event to a specific agent by agent_id."""
    # find session_id for this agent
    session_id = None
    for sid, aid in _session_agents.items():
        if aid == agent_id:
            session_id = sid
            break
    if session_id and session_id in _sse_channels:
        payload = {"type": event_type, "data": data}
        await _sse_channels[session_id].put(payload)


# ── SSE endpoint ──────────────────────────────────────────────────────────────


async def sse_endpoint(request: Request):
    """SSE endpoint for agents to connect and receive server-pushed events."""
    session_id = _new_session_id()
    queue: asyncio.Queue = asyncio.Queue()
    _sse_channels[session_id] = queue

    async def event_generator():
        # Send session_id as the first SSE event
        yield f"event: session\ndata: {json.dumps({'session_id': session_id})}\n\n"
        try:
            while True:
                try:
                    # wait for events with a 30s timeout to detect disconnects
                    msg = await asyncio.wait_for(queue.get(), timeout=30)
                    event_type = msg.get("type", "message")
                    data = json.dumps(msg.get("data", {}), default=str)
                    yield f"event: {event_type}\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    # SSE keepalive comment
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            # cleanup
            _sse_channels.pop(session_id, None)
            agent_id = _session_agents.pop(session_id, None)
            if agent_id:
                agent = get(agent_id)
                if agent:
                    update_status(agent_id, AgentStatus.OFFLINE)
                    await broadcast_event("agent.offline", agent.model_dump(mode="json"))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── JSON-RPC message handler ─────────────────────────────────────────────────


async def handle_message(session_id: str, body: dict) -> dict:
    """Process a JSON-RPC 2.0 message from an agent.

    Returns a JSON-RPC response dict.
    """
    method = body.get("method", "")
    params = body.get("params", {})
    msg_id = body.get("id")

    def _ok(result):
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    def _err(code: int, message: str):
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}

    try:
        # ── Agent registration ──
        if method == "agent.register":
            req = AgentRegisterRequest(**params)
            # get IP from existing session agent or use unknown
            existing_agent_id = _session_agents.get(session_id)
            existing_ip = ""
            if existing_agent_id:
                existing = get(existing_agent_id)
                if existing:
                    existing_ip = existing.ip

            agent = Agent(
                name=req.name,
                project=req.project,
                ip=existing_ip,
                capabilities=req.capabilities,
            )
            agent = register(agent)
            _session_agents[session_id] = agent.id
            await broadcast_event("agent.online", agent.model_dump(mode="json"))
            return _ok(agent.model_dump(mode="json"))

        # ── Agent heartbeat ──
        if method == "agent.heartbeat":
            agent_id = _session_agents.get(session_id)
            if not agent_id:
                return _err(-32001, "Not registered. Call agent.register first.")
            agent = update_heartbeat(agent_id)
            if agent:
                await broadcast_event("agent.updated", agent.model_dump(mode="json"))
                return _ok({"status": "ok", "timestamp": agent.last_heartbeat.isoformat()})
            return _err(-32002, "Agent not found.")

        # ── Agent status update ──
        if method == "agent.update_status":
            agent_id = _session_agents.get(session_id)
            if not agent_id:
                return _err(-32001, "Not registered.")
            status_str = params.get("status", "ONLINE")
            agent = update_status(agent_id, AgentStatus(status_str))
            if agent:
                await broadcast_event("agent.updated", agent.model_dump(mode="json"))
                return _ok(agent.model_dump(mode="json"))
            return _err(-32002, "Agent not found.")

        # ── List agents ──
        if method == "agent.list":
            agents = [a.model_dump(mode="json") for a in list_all()]
            return _ok(agents)

        # ── Task delegation ──
        if method == "task.delegate":
            agent_id = _session_agents.get(session_id)
            if not agent_id:
                return _err(-32001, "Not registered.")
            req = TaskDelegateRequest(**params)
            target = get(req.to_agent)
            if not target:
                return _err(-32003, f"Target agent '{req.to_agent}' not found.")
            task = create_task(
                title=req.title,
                description=req.description,
                from_agent=agent_id,
                to_agent=req.to_agent,
            )
            # Push task to target agent
            await _push_to_agent(req.to_agent, "task.assigned", task.model_dump(mode="json"))
            # Push update to frontend
            await broadcast_event("task.created", task.model_dump(mode="json"))
            return _ok(task.model_dump(mode="json"))

        # ── Task status update ──
        if method == "task.update":
            agent_id = _session_agents.get(session_id)
            if not agent_id:
                return _err(-32001, "Not registered.")
            task_id = params.get("task_id", "")
            req = TaskUpdateRequest(status=params.get("status"), result=params.get("result"))
            task = update_task(task_id, req.status, req.result)
            if not task:
                return _err(-32004, f"Task '{task_id}' not found.")

            # If task completed or failed, clear agent's current task
            if req.status in (TaskStatus.DONE, TaskStatus.FAILED):
                update_current_task(agent_id, None)
            else:
                update_current_task(agent_id, task_id)

            # Notify source agent of result
            await _push_to_agent(task.from_agent, "task.updated", task.model_dump(mode="json"))
            if req.status == TaskStatus.DONE:
                await _push_to_agent(task.from_agent, "task.result", task.model_dump(mode="json"))

            await broadcast_event("task.updated", task.model_dump(mode="json"))
            return _ok(task.model_dump(mode="json"))

        # ── List tasks ──
        if method == "task.list":
            agent_id = _session_agents.get(session_id)
            tasks = list_tasks(from_agent=agent_id)
            return _ok([t.model_dump(mode="json") for t in tasks])

        # ── MCP tools/list ──
        if method == "tools/list":
            return _ok({
                "tools": [
                    {"name": "agent.register", "description": "Register this agent with the bridge"},
                    {"name": "agent.heartbeat", "description": "Send heartbeat to keep connection alive"},
                    {"name": "agent.update_status", "description": "Update agent status"},
                    {"name": "agent.list", "description": "List all registered agents"},
                    {"name": "task.delegate", "description": "Delegate a task to another agent"},
                    {"name": "task.update", "description": "Update task status and result"},
                    {"name": "task.list", "description": "List tasks for this agent"},
                ]
            })

        return _err(-32601, f"Method '{method}' not found.")

    except Exception as exc:
        logger.exception("Error handling method %s", method)
        return _err(-32603, str(exc))


# ── WebSocket for frontend ───────────────────────────────────────────────────


async def frontend_ws(websocket):
    """WebSocket endpoint for the frontend dashboard."""
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue()
    _frontend_subscribers.append(queue)
    try:
        while True:
            try:
                # Check for client messages (e.g., pings)
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                    msg = json.loads(data)
                    # Handle subscription requests
                    if msg.get("type") == "subscribe":
                        pass  # Currently broadcast all events; could filter by channel
                except asyncio.TimeoutError:
                    pass

                # Push queued events to the client
                while not queue.empty():
                    payload = await queue.get()
                    await websocket.send_text(payload)

                await asyncio.sleep(0.5)
            except Exception as exc:
                logger.warning("WebSocket error: %s", exc)
                break
    finally:
        _frontend_subscribers.remove(queue)
