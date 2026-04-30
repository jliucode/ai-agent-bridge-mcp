"""MCP JSON-RPC 2.0 handler over SSE transport.

Supports both standard MCP protocol (initialize → tools/list → tools/call)
and custom JSON-RPC methods (agent.register, task.delegate, etc.).
"""

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

MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "ai-agent-bridge"
SERVER_VERSION = "1.0.0"

# SSE channels: session_id -> asyncio.Queue
_sse_channels: dict[str, asyncio.Queue] = {}

# session_id -> agent_id mapping
_session_agents: dict[str, str] = {}

# session_id -> client_info from initialize
_session_clients: dict[str, dict] = {}

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
    session_id = None
    for sid, aid in _session_agents.items():
        if aid == agent_id:
            session_id = sid
            break
    if session_id and session_id in _sse_channels:
        payload = {"type": event_type, "data": data}
        await _sse_channels[session_id].put(payload)


# ── MCP tool definitions ─────────────────────────────────────────────────────

MCP_TOOLS = [
    {
        "name": "agent_register",
        "description": "Register this agent with the bridge. Call this first to appear on the dashboard.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Human-readable agent name"},
                "project": {"type": "string", "description": "Project this agent is working on"},
                "capabilities": {
                    "type": "object",
                    "properties": {
                        "mcp_servers": {"type": "array", "items": {"type": "string"}, "description": "MCP servers this agent has access to"},
                        "skills": {"type": "array", "items": {"type": "string"}, "description": "Skills this agent can perform"},
                        "description": {"type": "string", "description": "What this agent does"},
                    },
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "agent_heartbeat",
        "description": "Send a heartbeat to keep this agent online. Call every 30 seconds.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "agent_update_status",
        "description": "Update this agent's status (ONLINE, BUSY, IDLE).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["ONLINE", "BUSY", "IDLE", "OFFLINE"]},
            },
            "required": ["status"],
        },
    },
    {
        "name": "agent_list",
        "description": "List all agents currently registered on the bridge.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "task_delegate",
        "description": "Delegate a task to another agent. The target agent will receive it via SSE and the result will be returned.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short task title"},
                "description": {"type": "string", "description": "Detailed task description"},
                "to_agent": {"type": "string", "description": "Target agent ID (get from agent_list)"},
            },
            "required": ["title", "to_agent"],
        },
    },
    {
        "name": "task_update",
        "description": "Update a task's status and optionally set the result.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID to update"},
                "status": {"type": "string", "enum": ["PENDING", "IN_PROGRESS", "DONE", "FAILED"]},
                "result": {"type": "string", "description": "Result text when task is DONE or FAILED"},
            },
            "required": ["task_id", "status"],
        },
    },
    {
        "name": "task_list",
        "description": "List tasks for this agent.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


# ── SSE endpoint ──────────────────────────────────────────────────────────────


async def sse_endpoint(request: Request):
    """SSE endpoint for MCP clients (Claude Code, agents) to connect."""
    session_id = _new_session_id()
    queue: asyncio.Queue = asyncio.Queue()
    _sse_channels[session_id] = queue

    # Derive the messages URL from the request
    base_url = str(request.base_url).rstrip("/")
    messages_url = f"{base_url}/messages?session_id={session_id}"

    async def event_generator():
        # MCP spec: first event MUST be 'endpoint' with the POST URL
        yield f"event: endpoint\ndata: {messages_url}\n\n"
        # Also send session_id for custom clients
        yield f"event: session\ndata: {json.dumps({'session_id': session_id})}\n\n"
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=30)
                    event_type = msg.get("type", "message")
                    data = json.dumps(msg.get("data", {}), default=str)
                    yield f"event: {event_type}\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            _sse_channels.pop(session_id, None)
            agent_id = _session_agents.pop(session_id, None)
            _session_clients.pop(session_id, None)
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


# ── Internal method handlers ─────────────────────────────────────────────────


async def _handle_register(session_id: str, params: dict):
    """Register an agent. Returns agent dict."""
    req = AgentRegisterRequest(**params)
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
    return agent.model_dump(mode="json")


async def _handle_heartbeat(session_id: str, params: dict):
    agent_id = _session_agents.get(session_id)
    if not agent_id:
        raise ValueError("Not registered. Call agent_register first.")
    agent = update_heartbeat(agent_id)
    if not agent:
        raise ValueError("Agent not found.")
    await broadcast_event("agent.updated", agent.model_dump(mode="json"))
    return {"status": "ok", "timestamp": agent.last_heartbeat.isoformat()}


async def _handle_update_status(session_id: str, params: dict):
    agent_id = _session_agents.get(session_id)
    if not agent_id:
        raise ValueError("Not registered.")
    status_str = params.get("status", "ONLINE")
    agent = update_status(agent_id, AgentStatus(status_str))
    if not agent:
        raise ValueError("Agent not found.")
    await broadcast_event("agent.updated", agent.model_dump(mode="json"))
    return agent.model_dump(mode="json")


async def _handle_list_agents(session_id: str, params: dict):
    return [a.model_dump(mode="json") for a in list_all()]


async def _handle_delegate(session_id: str, params: dict):
    agent_id = _session_agents.get(session_id)
    if not agent_id:
        raise ValueError("Not registered.")
    req = TaskDelegateRequest(**params)
    target = get(req.to_agent)
    if not target:
        raise ValueError(f"Target agent '{req.to_agent}' not found.")
    task = create_task(
        title=req.title,
        description=req.description,
        from_agent=agent_id,
        to_agent=req.to_agent,
    )
    await _push_to_agent(req.to_agent, "task.assigned", task.model_dump(mode="json"))
    await broadcast_event("task.created", task.model_dump(mode="json"))
    return task.model_dump(mode="json")


async def _handle_task_update(session_id: str, params: dict):
    agent_id = _session_agents.get(session_id)
    if not agent_id:
        raise ValueError("Not registered.")
    task_id = params.get("task_id", "")
    req = TaskUpdateRequest(status=params.get("status"), result=params.get("result"))
    task = update_task(task_id, req.status, req.result)
    if not task:
        raise ValueError(f"Task '{task_id}' not found.")

    if req.status in (TaskStatus.DONE, TaskStatus.FAILED):
        update_current_task(agent_id, None)
    else:
        update_current_task(agent_id, task_id)

    await _push_to_agent(task.from_agent, "task.updated", task.model_dump(mode="json"))
    if req.status == TaskStatus.DONE:
        await _push_to_agent(task.from_agent, "task.result", task.model_dump(mode="json"))

    await broadcast_event("task.updated", task.model_dump(mode="json"))
    return task.model_dump(mode="json")


async def _handle_task_list(session_id: str, params: dict):
    agent_id = _session_agents.get(session_id)
    tasks = list_tasks(from_agent=agent_id)
    return [t.model_dump(mode="json") for t in tasks]


# Map method names to handlers
_METHOD_HANDLERS = {
    "agent.register": _handle_register,
    "agent_register": _handle_register,
    "agent.heartbeat": _handle_heartbeat,
    "agent_heartbeat": _handle_heartbeat,
    "agent.update_status": _handle_update_status,
    "agent_update_status": _handle_update_status,
    "agent.list": _handle_list_agents,
    "agent_list": _handle_list_agents,
    "task.delegate": _handle_delegate,
    "task_delegate": _handle_delegate,
    "task.update": _handle_task_update,
    "task_update": _handle_task_update,
    "task.list": _handle_task_list,
    "task_list": _handle_task_list,
}


# ── JSON-RPC message handler ─────────────────────────────────────────────────


async def handle_message(session_id: str, body: dict) -> Optional[dict]:
    """Process a JSON-RPC 2.0 message.

    Supports both standard MCP (initialize, tools/list, tools/call)
    and custom direct methods (agent.register, task.delegate, etc.).

    Returns a JSON-RPC response dict, or None for notifications.
    """
    method = body.get("method", "")
    params = body.get("params", {})
    msg_id = body.get("id")

    is_notification = msg_id is None

    def _ok(result):
        return None if is_notification else {"jsonrpc": "2.0", "id": msg_id, "result": result}

    def _err(code: int, message: str):
        if is_notification:
            return None
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}

    try:
        # ── MCP standard: initialize ──
        if method == "initialize":
            client_info = params.get("clientInfo", {})
            _session_clients[session_id] = client_info
            logger.info("MCP initialize from %s v%s (session=%s)",
                        client_info.get("name", "unknown"),
                        client_info.get("version", ""),
                        session_id)
            return _ok({
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            })

        # ── MCP standard: initialized notification ──
        if method == "notifications/initialized":
            logger.info("MCP client initialized (session=%s)", session_id)
            return None  # notification, no response

        # ── MCP standard: tools/list ──
        if method == "tools/list":
            return _ok({"tools": MCP_TOOLS})

        # ── MCP standard: tools/call ──
        if method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            handler = _METHOD_HANDLERS.get(tool_name)
            if not handler:
                return _err(-32601, f"Tool '{tool_name}' not found.")
            try:
                result = await handler(session_id, arguments)
                return _ok({"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]})
            except ValueError as exc:
                return _err(-32000, str(exc))

        # ── Direct method calls (both dot-notation and underscore) ──
        handler = _METHOD_HANDLERS.get(method)
        if handler:
            try:
                result = await handler(session_id, params)
                return _ok(result)
            except ValueError as exc:
                return _err(-32000, str(exc))

        # ── MCP ping ──
        if method == "ping":
            return _ok({})

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
