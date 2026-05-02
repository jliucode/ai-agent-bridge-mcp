"""Local Agent manager for MCP Proxy."""
import hashlib
import time
import os
from typing import Optional
from pydantic import BaseModel

from utils.logger import logger


class AgentInfo(BaseModel):
    """Agent information."""
    agent_id: str
    project: str
    skills: list[str]
    description: str = ""
    capabilities: dict = {}
    session_id: str
    pid: int
    status: str = "IDLE"
    pending_tasks: list = []


class AgentManager:
    """Manage local Agents connected to this proxy."""

    def __init__(self, bridge_client):
        self.bridge = bridge_client
        self.mcp_server = None
        self.agents: dict[str, AgentInfo] = {}
        self.sessions: dict[str, str] = {}  # session_id → agent_id
        self.remote_agents: list[dict] = []

    def set_mcp_server(self, mcp_server):
        """Set MCP server reference for Channel notifications."""
        self.mcp_server = mcp_server

    def generate_agent_id(self, project: str, pid: int) -> str:
        """Generate unique agent ID."""
        short_hash = hashlib.md5(
            f"{project}{pid}{time.time()}".encode()
        ).hexdigest()[:4]
        return f"{project}-{pid}-{short_hash}"

    async def register_agent(
        self,
        session_id: str,
        project: str,
        skills: list[str],
        description: str = "",
        capabilities: dict = {},
    ) -> dict:
        """Register or update agent."""
        pid = os.getpid()

        existing_agent_id = self.sessions.get(session_id)

        if existing_agent_id:
            agent = self.agents[existing_agent_id]
            if project:
                agent.project = project
            if skills:
                agent.skills = skills
            if description:
                agent.description = description
            if capabilities:
                agent.capabilities = capabilities
            agent_id = existing_agent_id
        else:
            agent_id = self.generate_agent_id(project, pid)
            agent = AgentInfo(
                agent_id=agent_id,
                project=project,
                skills=skills,
                description=description,
                capabilities=capabilities,
                session_id=session_id,
                pid=pid,
                status="IDLE",
                pending_tasks=[],
            )
            self.agents[agent_id] = agent
            self.sessions[session_id] = agent_id

        await self.bridge.send({
            "type": "agent_register",
            "agent_id": agent_id,
            "machine_ip": self.bridge.machine_ip,
            "project": agent.project,
            "skills": agent.skills,
            "description": agent.description,
            "capabilities": agent.capabilities,
        })

        logger.log_registered(agent_id, agent.project, agent.skills)

        return {
            "agent_id": agent_id,
            "status": agent.status,
            "pending_tasks": agent.pending_tasks,
        }

    def get_agent_by_session(self, session_id: str) -> Optional[AgentInfo]:
        """Get agent by session ID."""
        agent_id = self.sessions.get(session_id)
        if agent_id:
            return self.agents[agent_id]
        return None

    def get_pending_tasks(self, session_id: str) -> list:
        """Get pending tasks for agent."""
        agent = self.get_agent_by_session(session_id)
        if agent:
            return agent.pending_tasks
        return []

    def on_session_disconnect(self, session_id: str):
        """Handle session disconnect."""
        agent_id = self.sessions.get(session_id)
        if agent_id:
            agent = self.agents[agent_id]
            agent.status = "OFFLINE"
            logger.log_event("OFFLINE", agent.project, "Disconnected", agent_id, "❌")
            del self.sessions[session_id]
            del self.agents[agent_id]
            logger.update_stats(agents=len(self.agents))

    async def handle_task_assigned(self, msg: dict):
        """Handle task_assigned from Bridge."""
        agent_id = msg["agent_id"]
        task = msg["task"]

        if agent_id in self.agents:
            agent = self.agents[agent_id]
            agent.pending_tasks.append(task)
            agent.status = "BUSY"

            logger.log_task(task["task_id"], "Assigned", task["title"], "📥")

            if self.mcp_server:
                await self.mcp_server.notify_channel(
                    content=f"""新任务到达!
任务: {task['title']}
描述: {task['description']}
来自: {task['from_agent']}

建议操作:
1. 调用 get_pending_tasks 查看完整任务详情
2. 调用 task_update(status="IN_PROGRESS") 开始处理""",
                    meta={
                        "source": "agent-bridge",
                        "task_id": task["task_id"],
                        "type": "task_assigned",
                    }
                )

    async def handle_agents_sync(self, msg: dict):
        """Handle agents_sync from Bridge."""
        self.remote_agents = msg["agents"]
        logger.log_event("SYNC", "Remote", f"{len(self.remote_agents)} agents", "Updated", "✅")

    async def handle_task_result(self, msg: dict):
        """Handle task_result from Bridge."""
        for agent in self.agents.values():
            if agent.agent_id == msg.get("from_agent"):
                logger.log_task(msg["task_id"], msg["status"], msg.get("result", ""), "✅")
                break