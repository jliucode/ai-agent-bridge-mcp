"""WebSocket handler for MCP Proxy connections."""

import asyncio
import json
import time
import uuid
from typing import Dict

from fastapi import WebSocket, WebSocketDisconnect

from .agent_registry import agent_registry
from .task_manager import task_manager


class ProxyConnectionManager:
    """Manage WebSocket connections from MCP Proxies."""

    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}  # machine_ip → ws
        self.skill_tasks: Dict[str, dict] = {}  # task_id → task info

    async def connect(self, websocket: WebSocket, machine_ip: str):
        """Accept new connection."""
        await websocket.accept()
        self.connections[machine_ip] = websocket

        machine_id = f"machine-{machine_ip.replace('.', '-')}"
        await websocket.send_json({
            "type": "welcome",
            "machine_id": machine_id,
            "timestamp": time.time(),
        })

    async def disconnect(self, machine_ip: str):
        """Handle disconnect."""
        if machine_ip in self.connections:
            del self.connections[machine_ip]
        agent_registry.mark_machine_offline(machine_ip)

    async def send_to_machine(self, machine_ip: str, msg: dict):
        """Send message to specific machine."""
        ws = self.connections.get(machine_ip)
        if ws:
            await ws.send_json(msg)

    async def broadcast_agents_sync(self):
        """Broadcast agent sync to all proxies."""
        agents = agent_registry.list_all()
        msg = {
            "type": "agents_sync",
            "agents": agents,
            "timestamp": time.time(),
        }
        for ws in self.connections.values():
            await ws.send_json(msg)


proxy_manager = ProxyConnectionManager()


async def handle_proxy_message(websocket: WebSocket, machine_ip: str, msg: dict):
    """Handle message from MCP Proxy."""
    msg_type = msg.get("type")

    if msg_type == "machine_heartbeat":
        agent_registry.update_machine_heartbeat(
            machine_ip,
            msg.get("online_agents", [])
        )

    elif msg_type == "agent_register":
        agent_id = msg["agent_id"]
        agent_registry.register(
            agent_id=agent_id,
            project=msg["project"],
            skills=msg.get("skills", []),
            description=msg.get("description", ""),
            capabilities=msg.get("capabilities", {}),
            machine_ip=machine_ip,
            status="IDLE",
        )
        pending = task_manager.get_pending_tasks(agent_id)
        await websocket.send_json({
            "type": "agent_registered",
            "agent_id": agent_id,
            "pending_tasks": pending,
        })
        await proxy_manager.broadcast_agents_sync()

    elif msg_type == "task_delegate":
        result = await task_manager.delegate_task(
            from_agent=msg["from_agent"],
            from_machine=machine_ip,
            to_project=msg["to_project"],
            title=msg["title"],
            description=msg["description"],
        )
        await websocket.send_json(result)

    elif msg_type == "task_update":
        task_manager.update_task(
            task_id=msg["task_id"],
            status=msg["status"],
            result=msg.get("result"),
        )
        task = task_manager.get_task(msg["task_id"])
        if task and task.get("from_machine"):
            await proxy_manager.send_to_machine(task["from_machine"], {
                "type": "task_result",
                "task_id": msg["task_id"],
                "status": msg["status"],
                "result": msg.get("result"),
            })

    elif msg_type == "skill_call":
        task_id = msg["task_id"]
        to_agent = msg["to_agent"]
        to_machine = msg["to_machine"]

        # Store task for result tracking
        proxy_manager.skill_tasks[task_id] = {
            "from_agent": msg["from_agent"],
            "from_machine": msg["from_machine"],
            "task_id": task_id,
        }

        # Forward to target machine
        await proxy_manager.send_to_machine(to_machine, {
            "type": "skill_call",
            "task_id": task_id,
            "skill": msg["skill"],
            "action": msg["action"],
            "params": msg["params"],
            "files": msg.get("files", []),
            "from_agent": msg["from_agent"],
            "to_agent": to_agent,
            "is_local": msg.get("is_local", False),
        })

    elif msg_type == "skill_result":
        task_id = msg["task_id"]
        task = proxy_manager.skill_tasks.get(task_id)

        if task:
            # Send result back to source machine
            await proxy_manager.send_to_machine(task["from_machine"], {
                "type": "skill_result",
                "task_id": task_id,
                "result": msg["result"],
                "status": msg["status"],
            })
            proxy_manager.skill_tasks.pop(task_id, None)