"""Agent registry — in-memory store for connected agents."""

import logging
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from .models import Agent, AgentStatus

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Manage registered agents."""

    def __init__(self):
        self.agents: dict[str, dict] = {}

    def register(
        self,
        agent_id: str,
        project: str,
        machine_ip: str,
        skills: list[str] = None,
        description: str = "",
        capabilities: dict = None,
        status: str = "IDLE",
    ) -> dict:
        """Register a new agent or update an existing one."""
        now = time.time()
        agent = {
            "agent_id": agent_id,
            "project": project,
            "machine_ip": machine_ip,
            "skills": skills or [],
            "description": description,
            "capabilities": capabilities or {},
            "status": status,
            "last_heartbeat": now,
            "connected_at": now,
        }
        self.agents[agent_id] = agent
        logger.info("Agent registered: %s (project=%s, machine=%s)", agent_id, project, machine_ip)
        return agent

    def unregister(self, agent_id: str) -> Optional[dict]:
        """Remove an agent from the registry."""
        agent = self.agents.pop(agent_id, None)
        if agent:
            logger.info("Agent unregistered: %s", agent_id)
        return agent

    def get(self, agent_id: str) -> Optional[dict]:
        """Get an agent by id."""
        return self.agents.get(agent_id)

    def find_by_project(self, project: str) -> list[dict]:
        """Find agents by project name."""
        return [a for a in self.agents.values() if a.get("project") == project]

    def find_by_machine(self, machine_ip: str) -> list[dict]:
        """Find agents by machine IP."""
        return [a for a in self.agents.values() if a.get("machine_ip") == machine_ip]

    def list_all(self) -> list[dict]:
        """Return all registered agents."""
        return list(self.agents.values())

    def update_heartbeat(self, agent_id: str) -> Optional[dict]:
        """Update the last heartbeat timestamp for an agent."""
        agent = self.agents.get(agent_id)
        if agent:
            agent["last_heartbeat"] = time.time()
            # auto-transition IDLE -> ONLINE on heartbeat
            if agent.get("status") == "IDLE":
                agent["status"] = "ONLINE"
        return agent

    def update_status(self, agent_id: str, status: str) -> Optional[dict]:
        """Update agent status."""
        agent = self.agents.get(agent_id)
        if agent:
            agent["status"] = status
            logger.info("Agent %s status -> %s", agent_id, status)
        return agent

    def update_machine_heartbeat(self, machine_ip: str, online_agents: list[str]):
        """Update heartbeat for agents on a machine."""
        now = time.time()
        for agent_id, agent in self.agents.items():
            if agent.get("machine_ip") == machine_ip:
                agent["last_heartbeat"] = now
                if agent_id in online_agents:
                    agent["status"] = "IDLE"
                    logger.debug("Agent %s on machine %s is IDLE", agent_id, machine_ip)

    def mark_machine_offline(self, machine_ip: str):
        """Mark all agents on a machine as offline."""
        for agent in self.agents.values():
            if agent.get("machine_ip") == machine_ip:
                agent["status"] = "OFFLINE"
                logger.info("Agent %s on machine %s marked OFFLINE", agent.get("agent_id"), machine_ip)

    def mark_offline_stale(self, heartbeat_timeout_seconds: int = 60) -> list[dict]:
        """Mark agents that haven't sent a heartbeat recently as OFFLINE."""
        now = time.time()
        stale = []
        for agent in self.list_all():
            last_hb = agent.get("last_heartbeat")
            if last_hb is None:
                continue
            if now - last_hb > heartbeat_timeout_seconds:
                if agent.get("status") != "OFFLINE":
                    agent["status"] = "OFFLINE"
                    stale.append(agent)
                    logger.info("Agent %s marked offline (stale heartbeat)", agent.get("agent_id"))
        return stale


# Global instance
agent_registry = AgentRegistry()


# Module-level function aliases for backward compatibility
def register(agent: Agent) -> Agent:
    """Register a new agent or update an existing one."""
    agent.status = AgentStatus.ONLINE
    agent.connected_at = datetime.now(timezone.utc)
    agent.last_heartbeat = datetime.now(timezone.utc)
    # Note: This uses the Pydantic Agent model, stored separately
    return agent


def unregister(agent_id: str) -> Optional[Agent]:
    """Remove an agent from the registry."""
    # This is kept for backward compatibility with Pydantic model storage
    from .models import Agent
    agent_dict = agent_registry.unregister(agent_id)
    if agent_dict:
        return Agent(
            id=agent_id,
            name=agent_dict.get("agent_id", ""),
            project=agent_dict.get("project", ""),
            ip=agent_dict.get("machine_ip", ""),
            status=AgentStatus(agent_dict.get("status", "OFFLINE")),
            last_heartbeat=datetime.fromtimestamp(agent_dict.get("last_heartbeat", 0), tz=timezone.utc) if agent_dict.get("last_heartbeat") else None,
        )
    return None