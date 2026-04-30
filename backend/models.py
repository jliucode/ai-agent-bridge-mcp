"""Pydantic data models for the AI Agent Bridge."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _now():
    return datetime.now(timezone.utc)


def _new_id():
    return uuid4().hex[:12]


class AgentStatus(str, Enum):
    ONLINE = "ONLINE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"
    IDLE = "IDLE"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    FAILED = "FAILED"


class AgentCapability(BaseModel):
    mcp_servers: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    description: str = ""


class Agent(BaseModel):
    id: str = Field(default_factory=_new_id)
    name: str
    project: str = ""
    ip: str = ""
    status: AgentStatus = AgentStatus.OFFLINE
    capabilities: AgentCapability = Field(default_factory=AgentCapability)
    current_task: Optional[str] = None
    last_heartbeat: Optional[datetime] = None
    connected_at: Optional[datetime] = None


class AgentRegisterRequest(BaseModel):
    """Payload when an agent registers via MCP."""
    name: str
    project: str = ""
    capabilities: AgentCapability = Field(default_factory=AgentCapability)


class Task(BaseModel):
    id: str = Field(default_factory=_new_id)
    title: str
    description: str = ""
    from_agent: str
    to_agent: str
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class TaskDelegateRequest(BaseModel):
    """Payload when an agent delegates a task to another agent."""
    title: str
    description: str = ""
    to_agent: str


class TaskUpdateRequest(BaseModel):
    """Payload when an agent updates task status."""
    status: TaskStatus
    result: Optional[str] = None
