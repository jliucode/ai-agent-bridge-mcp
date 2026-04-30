"""Agent registry — in-memory store for connected agents."""

import logging
from datetime import datetime, timezone
from typing import Optional

from .models import Agent, AgentStatus

logger = logging.getLogger(__name__)

_registry: dict[str, Agent] = {}


def register(agent: Agent) -> Agent:
    """Register a new agent or update an existing one."""
    agent.status = AgentStatus.ONLINE
    agent.connected_at = datetime.now(timezone.utc)
    agent.last_heartbeat = datetime.now(timezone.utc)
    _registry[agent.id] = agent
    logger.info("Agent registered: %s (%s)", agent.name, agent.id)
    return agent


def unregister(agent_id: str) -> Optional[Agent]:
    """Remove an agent from the registry."""
    agent = _registry.pop(agent_id, None)
    if agent:
        agent.status = AgentStatus.OFFLINE
        logger.info("Agent unregistered: %s (%s)", agent.name, agent.id)
    return agent


def get(agent_id: str) -> Optional[Agent]:
    """Get an agent by id."""
    return _registry.get(agent_id)


def list_all() -> list[Agent]:
    """Return all registered agents."""
    return list(_registry.values())


def update_heartbeat(agent_id: str) -> Optional[Agent]:
    """Update the last heartbeat timestamp for an agent."""
    agent = _registry.get(agent_id)
    if agent:
        agent.last_heartbeat = datetime.now(timezone.utc)
        # auto-transition IDLE -> ONLINE on heartbeat
        if agent.status == AgentStatus.IDLE:
            agent.status = AgentStatus.ONLINE
    return agent


def update_status(agent_id: str, status: AgentStatus) -> Optional[Agent]:
    """Update agent status."""
    agent = _registry.get(agent_id)
    if agent:
        agent.status = status
        logger.info("Agent %s status -> %s", agent.name, status.value)
    return agent


def update_current_task(agent_id: str, task_id: Optional[str]) -> Optional[Agent]:
    """Set or clear the current task for an agent."""
    agent = _registry.get(agent_id)
    if agent:
        agent.current_task = task_id
        if task_id:
            agent.status = AgentStatus.BUSY
        else:
            agent.status = AgentStatus.ONLINE
    return agent


def mark_offline_stale(heartbeat_timeout_seconds: int = 60) -> list[Agent]:
    """Mark agents that haven't sent a heartbeat recently as OFFLINE."""
    now = datetime.now(timezone.utc)
    stale = []
    for agent in list_all():
        if agent.last_heartbeat is None:
            continue
        if (now - agent.last_heartbeat).total_seconds() > heartbeat_timeout_seconds:
            if agent.status != AgentStatus.OFFLINE:
                agent.status = AgentStatus.OFFLINE
                stale.append(agent)
                logger.info("Agent %s marked offline (stale heartbeat)", agent.name)
    return stale
