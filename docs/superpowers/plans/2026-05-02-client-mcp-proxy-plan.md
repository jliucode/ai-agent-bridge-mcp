# Client-Side MCP Proxy 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现用户机器上的常驻 MCP 代理，作为本地 Agent 与远程 Bridge 的中介层，实现多机器 Agent 功能池共享。

**Architecture:** MCP 代理通过 WebSocket 连接 Bridge，本地 Agent 通过 MCP stdio 连接代理。代理暴露动态 tools 供 Agent 注册、委派任务、调用远程技能。通过 Channel 推送任务通知给运行中的 Agent。

**Tech Stack:** Python 3.11+, MCP SDK, WebSockets, Rich (CLI表格), Pydantic, asyncio

---

## 文件结构

```
client/
├── main.py                 # 入口：启动 MCP 代理
├── config.py               # 配置加载（.env）
├── bridge_client.py        # WebSocket 连接 Bridge
├── mcp_server.py           # MCP Server（stdio + Channel）
├── agent_manager.py        # 本地 Agent 管理器
├── remote_agents_cache.py  # 远程 Agent 缓存（Phase 4）
├── llm_router.py           # LLM 路由决策（Phase 5）
├── tools/
│   ├── __init__.py
│   ├── agent_tools.py      # agent_register, get_pending_tasks
│   ├── task_tools.py       # task_delegate, task_update
│   └── remote_skill.py     # remote_skill（Phase 4）
├── utils/
│   ├── __init__.py
│   ├── logger.py           # CLI 表格日志
│   ├── file_transfer.py    # 文件传输（Phase 4）
├── .env.example            # 配置示例
└── requirements.txt        # 依赖

backend/
├── websocket_handler.py    # 新增：/ws_proxy 端点
├── agent_registry.py       # 修改：支持 machine_ip
├── task_manager.py         # 修改：支持 project 路由
├── llm_router.py           # 新增：LLM 路由（Phase 5）
```

---

## Phase 1: MCP 代理基础架构

### Task 1.1: 创建 client 目录和基础文件

**Files:**
- Create: `client/__init__.py`
- Create: `client/requirements.txt`
- Create: `client/.env.example`

- [ ] **Step 1: 创建 client 目录结构**

```bash
mkdir -p client/tools client/utils
touch client/__init__.py client/tools/__init__.py client/utils/__init__.py
```

- [ ] **Step 2: 创建 requirements.txt**

```txt
mcp>=1.0.0
websockets>=12.0
rich>=13.0
python-dotenv>=1.0
pydantic>=2.0
psutil>=5.9
httpx>=0.25
```

- [ ] **Step 3: 创建 .env.example**

```env
BRIDGE_URL=ws://localhost:8000/ws_proxy
LOG_LEVEL=INFO
LLM_ENABLED=false
LLM_PROVIDER=qwen
DASHSCOPE_API_KEY=
DASHSCOPE_MODEL_NAME=qwen-max
```

- [ ] **Step 4: Commit**

```bash
git add client/
git commit -m "feat(client): init client directory structure"
```

---

### Task 1.2: 实现配置加载模块

**Files:**
- Create: `client/config.py`

- [ ] **Step 1: 编写配置模块**

```python
"""Configuration loader for MCP Proxy."""
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel


class Config(BaseModel):
    """MCP Proxy configuration."""
    bridge_url: str = "ws://localhost:8000/ws_proxy"
    log_level: str = "INFO"
    llm_enabled: bool = False
    llm_provider: str = "qwen"
    dashscope_api_key: str = ""
    dashscope_model_name: str = "qwen-max"

    @classmethod
    def load(cls) -> Config:
        """Load configuration from .env file."""
        env_path = Path(__file__).parent / ".env"
        load_dotenv(env_path)

        return cls(
            bridge_url=os.getenv("BRIDGE_URL", "ws://localhost:8000/ws_proxy"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            llm_enabled=os.getenv("LLM_ENABLED", "false").lower() == "true",
            llm_provider=os.getenv("LLM_PROVIDER", "qwen"),
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY", ""),
            dashscope_model_name=os.getenv("DASHSCOPE_MODEL_NAME", "qwen-max"),
        )


config = Config.load()
```

- [ ] **Step 2: Commit**

```bash
git add client/config.py
git commit -m "feat(client): add config loader module"
```

---

### Task 1.3: 实现CLI 表格日志模块

**Files:**
- Create: `client/utils/logger.py`

- [ ] **Step 1: 编写日志模块**

```python
"""CLI table logger for MCP Proxy."""
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live


class ProxyLogger:
    """Rich-based table logger for MCP Proxy."""

    def __init__(self, machine_ip: str = "unknown"):
        self.console = Console()
        self.machine_ip = machine_ip
        self.events: list[dict] = []
        self.stats = {
            "agents_online": 0,
            "tasks_pending": 0,
            "last_hb": None,
        }

    def print_header(self, version: str = "0.1.0"):
        """Print header panel."""
        panel = Panel(
            f"[bold]MCP Proxy v{version}[/bold] — Machine: [cyan]{self.machine_ip}[/cyan]",
            style="blue"
        )
        self.console.print(panel)

    def log_event(
        self,
        event: str,
        target: str,
        status: str,
        details: str,
        status_icon: str = "✅"
    ):
        """Log an event to the table."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.events.append({
            "time": timestamp,
            "event": event,
            "target": target,
            "status": f"{status_icon} {status}",
            "details": details,
        })
        self._render_table()

    def _render_table(self):
        """Render the events table."""
        table = Table(title="MCP Proxy Events")
        table.add_column("Time", style="cyan")
        table.add_column("Event", style="green")
        table.add_column("Target", style="yellow")
        table.add_column("Status", style="magenta")
        table.add_column("Details", style="white")

        # Show last 10 events
        for event in self.events[-10:]:
            table.add_row(
                event["time"],
                event["event"],
                event["target"],
                event["status"],
                event["details"],
            )

        self.console.clear()
        self.print_header()
        self.console.print(table)
        self._print_stats()

    def _print_stats(self):
        """Print stats bar."""
        stats_line = (
            f"Agents Online: [cyan]{self.stats['agents_online']}[/cyan] │ "
            f"Tasks Pending: [yellow]{self.stats['tasks_pending']}[/yellow] │ "
            f"Last HB: [green]{self.stats['last_hb'] or 'N/A'}[/green]"
        )
        self.console.print(stats_line)

    def update_stats(self, agents: int = None, tasks: int = None, last_hb: str = None):
        """Update stats."""
        if agents is not None:
            self.stats["agents_online"] = agents
        if tasks is not None:
            self.stats["tasks_pending"] = tasks
        if last_hb is not None:
            self.stats["last_hb"] = last_hb
        self._render_table()

    def log_connected(self, bridge_url: str):
        """Log Bridge connection."""
        self.log_event("CONNECTED", "Bridge", "Online", bridge_url, "✅")

    def log_registered(self, agent_id: str, project: str, skills: list[str]):
        """Log Agent registration."""
        skills_str = ", ".join(skills[:3])
        if len(skills) > 3:
            skills_str += "..."
        short_id = agent_id.split("-")[0]
        self.log_event("REGISTERED", f"{project}-{short_id}", "IDLE", skills_str, "✅")
        self.stats["agents_online"] += 1

    def log_task(self, task_id: str, status: str, details: str, icon: str = "🔄"):
        """Log task event."""
        self.log_event("TASK", f"#{task_id}", status, details, icon)

    def log_heartbeat(self, agent_count: int):
        """Log heartbeat."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_event("HEARTBEAT", f"All ({agent_count})", "OK", "30s interval", "✅")
        self.update_stats(last_hb=timestamp)

    def log_error(self, message: str):
        """Log error."""
        self.log_event("ERROR", "System", "Failed", message, "❌")


logger = ProxyLogger()
```

- [ ] **Step 2: Commit**

```bash
git add client/utils/logger.py
git commit -m "feat(client): add Rich-based table logger"
```

---

### Task 1.4: 实现 WebSocket Bridge客户端

**Files:**
- Create: `client/bridge_client.py`

- [ ] **Step 1: 编写 Bridge 客户端**

```python
"""WebSocket client for Bridge Server connection."""
import asyncio
import json
import time
from typing import Callable, Optional
import websockets
from websockets.client import WebSocketClientProtocol

from config import config
from utils.logger import logger


class BridgeClient:
    """WebSocket client connecting to Bridge Server."""

    def __init__(self, machine_ip: str):
        self.machine_ip = machine_ip
        self.ws: Optional[WebSocketClientProtocol] = None
        self.machine_id: Optional[str] = None
        self.connected = False
        self._message_handlers: dict[str, Callable] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None

    def on_message(self, msg_type: str, handler: Callable):
        """Register message handler."""
        self._message_handlers[msg_type] = handler

    async def connect(self):
        """Connect to Bridge Server."""
        try:
            self.ws = await websockets.connect(config.bridge_url)
            self.connected = True

            # Send hello
            await self.send({
                "type": "hello",
                "machine_ip": self.machine_ip,
            })

            logger.log_connected(config.bridge_url)

            # Start heartbeat loop
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        except Exception as e:
            logger.log_error(f"Connection failed: {e}")
            self.connected = False

    async def send(self, msg: dict):
        """Send message to Bridge."""
        if self.ws:
            await self.ws.send(json.dumps(msg))

    async def receive_loop(self):
        """Receive messages from Bridge."""
        if not self.ws:
            return

        try:
            for msg_str in self.ws:
                msg = json.loads(msg_str)
                msg_type = msg.get("type")

                if msg_type == "welcome":
                    self.machine_id = msg.get("machine_id")
                    logger.log_event("WELCOME", "Bridge", "Ready", self.machine_id, "✅")

                elif msg_type in self._message_handlers:
                    await self._message_handlers[msg_type](msg)

        except websockets.ConnectionClosed:
            self.connected = False
            logger.log_error("Connection closed")
        except Exception as e:
            logger.log_error(f"Receive error: {e}")

    async def _heartbeat_loop(self):
        """Send heartbeat every 30 seconds."""
        while self.connected:
            await asyncio.sleep(30)
            if self.connected:
                await self.send({
                    "type": "machine_heartbeat",
                    "machine_ip": self.machine_ip,
                    "timestamp": time.time(),
                })

    async def close(self):
        """Close connection."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self.ws:
            await self.ws.close()
        self.connected = False
```

- [ ] **Step 2: Commit**

```bash
git add client/bridge_client.py
git commit -m "feat(client): add WebSocket Bridge client"
```

---

### Task 1.5: 实现 MCP Server 核心

**Files:**
- Create: `client/mcp_server.py`

- [ ] **Step 1: 编写 MCP Server**

```python
"""MCP Server implementation with Channel support."""
import asyncio
from typing import Callable
from mcp.server import Server
from mcp.server.stdio import stdio_server

from config import config


class MCPProxyServer:
    """MCP Server that exposes tools and supports Channel notifications."""

    def __init__(self, bridge_client, agent_manager):
        self.bridge = bridge_client
        self.agent_manager = agent_manager
        self.server = Server(
            {"name": "agent-bridge-proxy", "version": "0.1.0"},
            {
                "capabilities": {
                    "tools": {},
                    "experimental": {"claude/channel": {}},
                },
                "instructions": """
Agent Bridge Proxy - 连接到远程 Bridge，管理本地 Agent。

可用功能：
- agent_register: 注册/更新 Agent 信息
- task_delegate: 委派任务给其他项目
- get_pending_tasks: 查询待处理任务
- task_update: 更新任务状态
- list_remote_agents: 查询远程 Agent列表
- remote_skill: 调用远程 Agent 的技能（Phase 4）

当收到任务通知时，Channel 会推送消息到终端。
""",
            },
        )
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup MCP handlers."""
        @self.server.list_tools()
        async def list_tools():
            from tools.agent_tools import AGENT_TOOLS
            from tools.task_tools import TASK_TOOLS
            return AGENT_TOOLS + TASK_TOOLS

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict):
            return await self._handle_tool_call(name, arguments)

    async def _handle_tool_call(self, name: str, arguments: dict):
        """Handle tool call."""
        from tools.agent_tools import handle_agent_register, handle_get_pending_tasks, handle_list_remote_agents
        from tools.task_tools import handle_task_delegate, handle_task_update

        handlers = {
            "agent_register": handle_agent_register,
            "get_pending_tasks": handle_get_pending_tasks,
            "list_remote_agents": handle_list_remote_agents,
            "task_delegate": handle_task_delegate,
            "task_update": handle_task_update,
        }

        handler = handlers.get(name)
        if handler:
            return await handler(self, arguments)
        else:
            return [{"type": "text", "text": f"Unknown tool: {name}"}]

    async def notify_channel(self, content: str, meta: dict):
        """Push notification via Channel."""
        await self.server.notification({
            "method": "notifications/claude/channel",
            "params": {
                "content": content,
                "meta": meta,
            },
        })

    async def run(self):
        """Run MCP server over stdio."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )
```

- [ ] **Step 2: Commit**

```bash
git add client/mcp_server.py
git commit -m "feat(client): add MCP Server with Channel support"
```

---

### Task 1.6: 实现入口 main.py

**Files:**
- Create: `client/main.py`

- [ ] **Step 1: 编写主入口**

```python
"""MCP Proxy entry point."""
import asyncio
import socket
import sys
from pathlib import Path

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from bridge_client import BridgeClient
from mcp_server import MCPProxyServer
from agent_manager import AgentManager
from utils.logger import logger, ProxyLogger


def get_machine_ip() -> str:
    """Get local machine IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


async def main():
    """Main entry point."""
    machine_ip = get_machine_ip()

    # Initialize logger
    global logger
    logger = ProxyLogger(machine_ip)
    logger.print_header()

    # Initialize components
    bridge = BridgeClient(machine_ip)
    agent_manager = AgentManager(bridge)
    mcp_server = MCPProxyServer(bridge, agent_manager)

    # Register Bridge message handlers
    bridge.on_message("task_assigned", agent_manager.handle_task_assigned)
    bridge.on_message("agents_sync", agent_manager.handle_agents_sync)
    bridge.on_message("task_result", agent_manager.handle_task_result)

    # Connect to Bridge
    await bridge.connect()

    # Run MCP server and receive loop concurrently
    try:
        await asyncio.gather(
            mcp_server.run(),
            bridge.receive_loop(),
        )
    except KeyboardInterrupt:
        logger.log_event("SHUTDOWN", "System", "Stopped", "User interrupt", "⏹️")
        await bridge.close()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Commit**

```bash
git add client/main.py
git commit -m "feat(client): add main entry point"
```

---

### Task 1.7: 实现后端 WebSocket 端点

**Files:**
- Create: `backend/websocket_handler.py`
- Modify: `backend/server.py`

- [ ] **Step 1: 编写 WebSocket 处理器**

```python
"""WebSocket handler for MCP Proxy connections."""
import asyncio
import json
import time
from typing import dict
from fastapi import WebSocket, WebSocketDisconnect

from agent_registry import agent_registry
from task_manager import task_manager


class ProxyConnectionManager:
    """Manage WebSocket connections from MCP Proxies."""

    def __init__(self):
        self.connections: dict[str, WebSocket] = {}  # machine_ip → ws

    async def connect(self, websocket: WebSocket, machine_ip: str):
        """Accept new connection."""
        await websocket.accept()
        self.connections[machine_ip] = websocket

        # Send welcome
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
        # Mark all agents on this machine as OFFLINE
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
        # Update heartbeat for all agents on this machine
        agent_registry.update_machine_heartbeat(machine_ip, msg.get("online_agents", []))

    elif msg_type == "agent_register":
        # Register/update agent
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
        # Return pending tasks if any
        pending = task_manager.get_pending_tasks(agent_id)
        await websocket.send_json({
            "type": "agent_registered",
            "agent_id": agent_id,
            "pending_tasks": pending,
        })
        # Broadcast sync to all proxies
        await proxy_manager.broadcast_agents_sync()

    elif msg_type == "task_delegate":
        # Route task to target project
        result = await task_manager.delegate_task(
            from_agent=msg["from_agent"],
            to_project=msg["to_project"],
            title=msg["title"],
            description=msg["description"],
        )
        await websocket.send_json(result)

    elif msg_type == "task_update":
        # Update task status
        task_manager.update_task(
            task_id=msg["task_id"],
            status=msg["status"],
            result=msg.get("result"),
        )
        # Notify result to source machine
        task = task_manager.get_task(msg["task_id"])
        if task and task.get("from_machine"):
            await proxy_manager.send_to_machine(task["from_machine"], {
                "type": "task_result",
                "task_id": msg["task_id"],
                "status": msg["status"],
                "result": msg.get("result"),
            })

    elif msg_type == "skill_call":
        # Phase 4: Route skill call
        # TODO: Implement in Phase 4
        pass
```

- [ ] **Step 2: 修改 server.py 添加端点**

在 `backend/server.py` 中添加：

```python
from websocket_handler import proxy_manager, handle_proxy_message

@app.websocket("/ws_proxy")
async def ws_proxy_endpoint(websocket: WebSocket):
    """WebSocket endpoint for MCP Proxy connections."""
    machine_ip = None
    try:
        # Wait for hello message
        msg = await websocket.receive_json()
        if msg.get("type") != "hello":
            await websocket.close()
            return

        machine_ip = msg["machine_ip"]
        await proxy_manager.connect(websocket, machine_ip)

        # Message loop
        while True:
            msg = await websocket.receive_json()
            await handle_proxy_message(websocket, machine_ip, msg)

    except WebSocketDisconnect:
        if machine_ip:
            await proxy_manager.disconnect(machine_ip)
    except Exception as e:
        if machine_ip:
            await proxy_manager.disconnect(machine_ip)
```

- [ ] **Step 3: Commit**

```bash
git add backend/websocket_handler.py backend/server.py
git commit -m "feat(backend): add WebSocket /ws_proxy endpoint"
```

---

## Phase 2: Agent 注册与心跳

### Task 2.1: 实现 Agent 管理器

**Files:**
- Create: `client/agent_manager.py`

- [ ] **Step 1: 编写 Agent 管理器**

```python
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
        self.agents: dict[str, AgentInfo] = {}  # agent_id → info
        self.sessions: dict[str, str] = {}  # session_id → agent_id
        self.remote_agents: list[dict] = []

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

        # Check if session already has an agent
        existing_agent_id = self.sessions.get(session_id)

        if existing_agent_id:
            # Update existing agent
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
            # Create new agent
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

        # Send to Bridge
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

            # Push Channel notification
            session_id = agent.session_id
            # Note: Channel push requires MCP server reference
            # Will be handled in mcp_server.py

    async def handle_agents_sync(self, msg: dict):
        """Handle agents_sync from Bridge."""
        self.remote_agents = msg["agents"]
        logger.log_event("SYNC", "Remote", f"{len(self.remote_agents)} agents", "Updated", "✅")

    async def handle_task_result(self, msg: dict):
        """Handle task_result from Bridge (for source agent)."""
        # Find source agent and notify
        for agent in self.agents.values():
            if agent.agent_id == msg.get("from_agent"):
                logger.log_task(msg["task_id"], msg["status"], msg.get("result", ""), "✅")
                break
```

- [ ] **Step 2: Commit**

```bash
git add client/agent_manager.py
git commit -m "feat(client): add Agent manager with session tracking"
```

---

### Task 2.2: 实现 Agent Tools

**Files:**
- Create: `client/tools/agent_tools.py`

- [ ] **Step 1: 编写 Agent Tools 定义和处理**

```python
"""Agent management MCP tools."""
from mcp.types import Tool, TextContent


AGENT_TOOLS = [
    Tool(
        name="agent_register",
        description="注册或更新 Agent 信息。首次调用生成 agent_id，后续调用可更新信息。",
        inputSchema={
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": "项目名称",
                },
                "skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "技能列表（如 gitnexus, pptx, commit）",
                },
                "description": {
                    "type": "string",
                    "description": "Agent描述（可选）",
                },
                "capabilities": {
                    "type": "object",
                    "description": "详细能力（可选，如 MCP servers, tools）",
                },
            },
            "required": ["project", "skills"],
        },
    ),
    Tool(
        name="get_pending_tasks",
        description="查询当前 Agent 的待处理任务列表。",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="list_remote_agents",
        description="查询远程 Agent 列表（其他机器上的 Agent）。",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
]


async def handle_agent_register(mcp_server, arguments: dict) -> list:
    """Handle agent_register tool call."""
    session_id = mcp_server.server.session_id  # Get from MCP context

    result = await mcp_server.agent_manager.register_agent(
        session_id=session_id,
        project=arguments.get("project", ""),
        skills=arguments.get("skills", []),
        description=arguments.get("description", ""),
        capabilities=arguments.get("capabilities", {}),
    )

    return [
        TextContent(
            type="text",
            text=f"Agent 注册成功!\n"
                 f"ID: {result['agent_id']}\n"
                 f"状态: {result['status']}\n"
                 f"待处理任务: {len(result['pending_tasks'])}个",
        )
    ]


async def handle_get_pending_tasks(mcp_server, arguments: dict) -> list:
    """Handle get_pending_tasks tool call."""
    session_id = mcp_server.server.session_id

    tasks = mcp_server.agent_manager.get_pending_tasks(session_id)

    if not tasks:
        return [TextContent(type="text", text="无待处理任务")]

    lines = ["待处理任务列表:"]
    for task in tasks:
        lines.append(f"- #{task['task_id']}: {task['title']}")
        lines.append(f"  来自: {task['from_agent']}")
        lines.append(f"  描述: {task['description']}")

    return [TextContent(type="text", text="\n".join(lines))]


async def handle_list_remote_agents(mcp_server, arguments: dict) -> list:
    """Handle list_remote_agents tool call."""
    agents = mcp_server.agent_manager.remote_agents

    if not agents:
        return [TextContent(type="text", text="无远程 Agent")]

    lines = ["远程 Agent 列表:"]
    for agent in agents:
        status_icon = "✅" if agent["status"] == "IDLE" else "🔄"
        lines.append(f"- {agent['project']} ({agent['agent_id']}) {status_icon}")
        lines.append(f"  技能: {', '.join(agent['skills'])}")

    return [TextContent(type="text", text="\n".join(lines))]
```

- [ ] **Step 2: Commit**

```bash
git add client/tools/agent_tools.py
git commit -m "feat(client): add agent_register, get_pending_tasks, list_remote_agents tools"
```

---

## Phase 3: 任务获取与通知

### Task 3.1: 实现任务 Tools

**Files:**
- Create: `client/tools/task_tools.py`

- [ ] **Step 1: 编写任务 Tools**

```python
"""Task management MCP tools."""
from mcp.types import Tool, TextContent


TASK_TOOLS = [
    Tool(
        name="task_delegate",
        description="委派任务给其他项目的 Agent。",
        inputSchema={
            "type": "object",
            "properties": {
                "to_project": {
                    "type": "string",
                    "description": "目标项目名称",
                },
                "title": {
                    "type": "string",
                    "description": "任务标题",
                },
                "description": {
                    "type": "string",
                    "description": "任务详细描述",
                },
            },
            "required": ["to_project", "title", "description"],
        },
    ),
    Tool(
        name="task_update",
        description="更新任务状态（IN_PROGRESS, DONE, FAILED）。",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "任务 ID",
                },
                "status": {
                    "type": "string",
                    "enum": ["IN_PROGRESS", "DONE", "FAILED"],
                    "description": "任务状态",
                },
                "result": {
                    "type": "string",
                    "description": "任务结果或说明（可选）",
                },
            },
            "required": ["task_id", "status"],
        },
    ),
]


async def handle_task_delegate(mcp_server, arguments: dict) -> list:
    """Handle task_delegate tool call."""
    session_id = mcp_server.server.session_id
    agent = mcp_server.agent_manager.get_agent_by_session(session_id)

    if not agent:
        return [TextContent(type="text", text="错误: Agent 未注册")]

    # Send to Bridge
    await mcp_server.bridge.send({
        "type": "task_delegate",
        "from_agent": agent.agent_id,
        "from_machine": mcp_server.bridge.machine_ip,
        "to_project": arguments["to_project"],
        "title": arguments["title"],
        "description": arguments["description"],
    })

    return [
        TextContent(
            type="text",
            text=f"任务已委派!\n"
                 f"目标项目: {arguments['to_project']}\n"
                 f"任务: {arguments['title']}\n"
                 f"等待结果通知...",
        )
    ]


async def handle_task_update(mcp_server, arguments: dict) -> list:
    """Handle task_update tool call."""
    task_id = arguments["task_id"]
    status = arguments["status"]
    result = arguments.get("result", "")

    # Send to Bridge
    await mcp_server.bridge.send({
        "type": "task_update",
        "task_id": task_id,
        "status": status,
        "result": result,
    })

    logger.log_task(task_id, status, result, "🔄" if status == "IN_PROGRESS" else "✅")

    return [
        TextContent(
            type="text",
            text=f"任务状态已更新!\n"
                 f"ID: {task_id}\n"
                 f"状态: {status}",
        )
    ]
```

- [ ] **Step 2: Commit**

```bash
git add client/tools/task_tools.py
git commit -m "feat(client): add task_delegate, task_update tools"
```

---

### Task 3.2: 实现 Channel 任务通知

**Files:**
- Modify: `client/agent_manager.py`
- Modify: `client/mcp_server.py`

- [ ] **Step 1: 修改 agent_manager.py 添加 Channel 推送**

在 `AgentManager` 中添加对 `mcp_server` 的引用：

```python
class AgentManager:
    def __init__(self, bridge_client, mcp_server=None):
        self.bridge = bridge_client
        self.mcp_server = mcp_server
        # ... rest of init

    def set_mcp_server(self, mcp_server):
        """Set MCP server reference for Channel notifications."""
        self.mcp_server = mcp_server

    async def handle_task_assigned(self, msg: dict):
        """Handle task_assigned from Bridge."""
        agent_id = msg["agent_id"]
        task = msg["task"]

        if agent_id in self.agents:
            agent = self.agents[agent_id]
            agent.pending_tasks.append(task)
            agent.status = "BUSY"

            logger.log_task(task["task_id"], "Assigned", task["title"], "📥")

            # Push Channel notification
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
```

- [ ] **Step 2: 修改 main.py 传递 mcp_server**

```python
# In main.py, update initialization
agent_manager = AgentManager(bridge)
mcp_server = MCPProxyServer(bridge, agent_manager)
agent_manager.set_mcp_server(mcp_server)
```

- [ ] **Step 3: Commit**

```bash
git add client/agent_manager.py client/main.py
git commit -m "feat(client): add Channel notification for task_assigned"
```

---

### Task 3.3: 修改后端支持项目路由

**Files:**
- Modify: `backend/task_manager.py`

- [ ] **Step 1: 修改 task_manager.py 添加项目路由**

```python
# Add to TaskManager class

async def delegate_task(
    self,
    from_agent: str,
    from_machine: str,
    to_project: str,
    title: str,
    description: str,
) -> dict:
    """Delegate task to target project."""
    # Find agents for target project
    candidates = agent_registry.find_by_project(to_project)

    if not candidates:
        return {
            "type": "delegate_failed",
            "error": f"没有 Agent 在项目 {to_project}",
        }

    # Select agent (simple load balance for Phase 3)
    # Priority: IDLE > least tasks
    idle_agents = [a for a in candidates if a["status"] == "IDLE"]
    if idle_agents:
        target_agent = idle_agents[0]
    else:
        target_agent = min(candidates, key=lambda a: a.get("current_tasks", 0))

    # Create task
    task_id = f"task-{int(time.time())}-{uuid.uuid4().hex[:4]}"
    task = {
        "task_id": task_id,
        "from_agent": from_agent,
        "from_machine": from_machine,
        "to_agent": target_agent["agent_id"],
        "to_machine": target_agent["machine_ip"],
        "title": title,
        "description": description,
        "status": "PENDING",
        "created_at": time.time(),
    }
    self.tasks[task_id] = task

    # Notify target machine via WebSocket
    await proxy_manager.send_to_machine(target_agent["machine_ip"], {
        "type": "task_assigned",
        "agent_id": target_agent["agent_id"],
        "task": task,
    })

    return {
        "type": "delegate_success",
        "task_id": task_id,
        "target_agent": target_agent["agent_id"],
    }
```

- [ ] **Step 2: Commit**

```bash
git add backend/task_manager.py
git commit -m "feat(backend): add project-based task routing"
```

---

## Phase 4: 动态 MCP Tools

### Task 4.1: 实现远程 Agent 缓存

**Files:**
- Create: `client/remote_agents_cache.py`

- [ ] **Step 1: 编写远程 Agent 缓存**

```python
"""Remote agents cache with skill indexing."""
from typing import Optional


class RemoteAgentsCache:
    """Cache and index remote agents by skills."""

    def __init__(self):
        self.agents: dict[str, dict] = {}  # agent_id → info
        self.skills_index: dict[str, list[str]] = {}  # skill → agent_ids
        self.projects_index: dict[str, list[str]] = {}  # project → agent_ids

    def update(self, agents_list: list[dict]):
        """Update cache from Bridge sync."""
        self.agents = {a["agent_id"]: a for a in agents_list}

        # Rebuild indexes
        self.skills_index = {}
        self.projects_index = {}

        for agent in agents_list:
            for skill in agent.get("skills", []):
                self.skills_index.setdefault(skill, []).append(agent["agent_id"])

            project = agent.get("project")
            if project:
                self.projects_index.setdefault(project, []).append(agent["agent_id"])

    def find_by_skill(self, skill: str, project: Optional[str] = None) -> list[dict]:
        """Find agents with given skill."""
        candidates = self.skills_index.get(skill, [])
        if project:
            candidates = [c for c in candidates if self.agents[c]["project"] == project]
        return [self.agents[c] for c in candidates]

    def get_agent(self, agent_id: str) -> Optional[dict]:
        """Get agent by ID."""
        return self.agents.get(agent_id)

    def is_local(self, agent_id: str, local_agent_ids: list[str]) -> bool:
        """Check if agent is local."""
        return agent_id in local_agent_ids

    def select_agent(self, candidates: list[dict]) -> Optional[dict]:
        """Select best agent (load balance)."""
        if not candidates:
            return None

        # Priority: IDLE > least tasks
        idle = [a for a in candidates if a["status"] == "IDLE"]
        if idle:
            return idle[0]

        return min(candidates, key=lambda a: a.get("current_tasks", 0))
```

- [ ] **Step 2: Commit**

```bash
git add client/remote_agents_cache.py
git commit -m "feat(client): add remote agents cache with skill indexing"
```

---

### Task 4.2: 实现文件传输模块

**Files:**
- Create: `client/utils/file_transfer.py`

- [ ] **Step 1: 编写文件传输模块**

```python
"""File transfer utilities for remote skill calls."""
import base64
import os
import tempfile
from pathlib import Path
from typing import list


class FileTransfer:
    """Handle file transfer for remote skill calls."""

    @staticmethod
    def read_files(file_paths: list[str]) -> list[dict]:
        """Read files and encode for transfer."""
        files = []
        for path in file_paths:
            p = Path(path)
            if not p.exists():
                continue

            with open(p, "rb") as f:
                content = base64.b64encode(f.read()).decode()

            files.append({
                "original_path": path,
                "filename": p.name,
                "content": content,
                "size": p.stat().st_size,
            })
        return files

    @staticmethod
    def save_files(files: list[dict], task_id: str) -> list[str]:
        """Save transferred files to temp directory."""
        transfer_dir = Path(tempfile.gettempdir()) / "transfer" / task_id
        transfer_dir.mkdir(parents=True, exist_ok=True)

        local_paths = []
        for file in files:
            local_path = transfer_dir / file["filename"]
            with open(local_path, "wb") as f:
                f.write(base64.b64decode(file["content"]))
            local_paths.append(str(local_path))

        return local_paths

    @staticmethod
    def cleanup(task_id: str):
        """Clean up transferred files."""
        transfer_dir = Path(tempfile.gettempdir()) / "transfer" / task_id
        if transfer_dir.exists():
            for f in transfer_dir.iterdir():
                f.unlink()
            transfer_dir.rmdir()
```

- [ ] **Step 2: Commit**

```bash
git add client/utils/file_transfer.py
git commit -m "feat(client): add file transfer utilities"
```

---

### Task 4.3: 实现 remote_skill Tool

**Files:**
- Create: `client/tools/remote_skill.py`
- Modify: `client/mcp_server.py`

- [ ] **Step 1: 编写 remote_skill Tool**

```python
"""Remote skill MCP tool."""
import asyncio
import time
import uuid
from mcp.types import Tool, TextContent

from remote_agents_cache import RemoteAgentsCache
from utils.file_transfer import FileTransfer


REMOTE_SKILL_TOOL = Tool(
    name="remote_skill",
    description="调用远程 Agent 的技能。自动选择合适的 Agent，支持文件传输。",
    inputSchema={
        "type": "object",
        "properties": {
            "skill": {
                "type": "string",
                "description": "技能名称（如 gitnexus, pptx）",
            },
            "action": {
                "type": "string",
                "description": "具体操作（如 query, create）",
            },
            "params": {
                "type": "object",
                "description": "操作参数",
            },
            "to_project": {
                "type": "string",
                "description": "目标项目（可选，用于筛选）",
            },
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "需传输的文件路径（可选）",
            },
        },
        "required": ["skill", "action", "params"],
    },
)

# Global cache and pending results
remote_cache = RemoteAgentsCache()
pending_results: dict[str, asyncio.Future] = {}


async def handle_remote_skill(mcp_server, arguments: dict) -> list:
    """Handle remote_skill tool call."""
    skill = arguments["skill"]
    action = arguments["action"]
    params = arguments["params"]
    to_project = arguments.get("to_project")
    files = arguments.get("files", [])

    # Find candidates
    candidates = remote_cache.find_by_skill(skill, to_project)
    if not candidates:
        return [TextContent(type="text", text=f"没有 Agent 提供 {skill} 技能")]

    # Filter out offline agents
    candidates = [a for a in candidates if a["status"] != "OFFLINE"]
    if not candidates:
        return [TextContent(type="text", text=f"所有 {skill} Agent 都离线")]

    # Select target
    local_agent_ids = list(mcp_server.agent_manager.agents.keys())
    target = remote_cache.select_agent(candidates)
    is_local = remote_cache.is_local(target["agent_id"], local_agent_ids)

    # Generate task ID
    task_id = f"skill-{int(time.time())}-{uuid.uuid4().hex[:4]}"

    # Handle files
    file_data = []
    if files and not is_local:
        file_data = FileTransfer.read_files(files)

    # Get source agent
    session_id = mcp_server.server.session_id
    source_agent = mcp_server.agent_manager.get_agent_by_session(session_id)

    # Send to Bridge
    await mcp_server.bridge.send({
        "type": "skill_call",
        "task_id": task_id,
        "skill": skill,
        "action": action,
        "params": params,
        "files": file_data,
        "from_agent": source_agent.agent_id if source_agent else "unknown",
        "from_machine": mcp_server.bridge.machine_ip,
        "to_agent": target["agent_id"],
        "to_machine": target["machine_ip"],
        "is_local": is_local,
    })

    logger.log_event("SKILL_CALL", skill, "Calling", f"→ {target['project']}", "🔄")

    # Wait for result (synchronous call)
    future = asyncio.Future()
    pending_results[task_id] = future

    try:
        result = await asyncio.wait_for(future, timeout=120)
        logger.log_event("SKILL_CALL", skill, "Done", f"✅ {target['project']}", "✅")
        return [TextContent(type="text", text=f"远程技能调用结果:\n{result}")]
    except asyncio.TimeoutError:
        logger.log_error(f"技能调用超时: {task_id}")
        return [TextContent(type="text", text=f"调用超时 (120s)")]
    finally:
        pending_results.pop(task_id, None)


async def handle_skill_result(msg: dict):
    """Handle skill result from Bridge."""
    task_id = msg["task_id"]
    result = msg.get("result", "")

    if task_id in pending_results:
        pending_results[task_id].set_result(result)
```

- [ ] **Step 2: 修改 mcp_server.py 注册 tool**

```python
# In MCPProxyServer._setup_handlers()

@self.server.list_tools()
async def list_tools():
    from tools.agent_tools import AGENT_TOOLS
    from tools.task_tools import TASK_TOOLS
    from tools.remote_skill import REMOTE_SKILL_TOOL
    return AGENT_TOOLS + TASK_TOOLS + [REMOTE_SKILL_TOOL]

# In _handle_tool_call handlers dict
from tools.remote_skill import handle_remote_skill
handlers["remote_skill"] = handle_remote_skill
```

- [ ] **Step 3: 注册结果处理器**

```python
# In main.py
from tools.remote_skill import handle_skill_result
bridge.on_message("skill_result", handle_skill_result)
```

- [ ] **Step 4: Commit**

```bash
git add client/tools/remote_skill.py client/mcp_server.py client/main.py
git commit -m "feat(client): add remote_skill tool with sync call and file transfer"
```

---

### Task 4.4: 后端支持 skill_call 路由

**Files:**
- Modify: `backend/websocket_handler.py`

- [ ] **Step 1: 添加 skill_call 处理**

```python
# In handle_proxy_message()

elif msg_type == "skill_call":
    task_id = msg["task_id"]
    to_agent = msg["to_agent"]
    to_machine = msg["to_machine"]

    # Store task for result tracking
    skill_tasks[task_id] = {
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
    task = skill_tasks.get(task_id)

    if task:
        # Send result back to source machine
        await proxy_manager.send_to_machine(task["from_machine"], {
            "type": "skill_result",
            "task_id": task_id,
            "result": msg["result"],
            "status": msg["status"],
        })
        skill_tasks.pop(task_id, None)
```

- [ ] **Step 2: Commit**

```bash
git add backend/websocket_handler.py
git commit -m "feat(backend): add skill_call routing and result forwarding"
```

---

## Phase 5: LLM 智能调度

### Task 5.1: 实现 Bridge LLM Router

**Files:**
- Create: `backend/llm_router.py`

- [ ] **Step 1: 编写 LLM Router**

```python
"""LLM-based routing for Bridge Server."""
import json
import asyncio
from typing import Optional
import httpx

from config import config


BRIDGE_ROUTE_PROMPT = """你是一个任务路由决策助手。根据以下信息选择最合适的目标 Agent。

## 任务信息
- 类型: {task_type}
- 描述: {description}
- 需要技能: {required_skills}
- 目标项目: {target_project}

## 候选 Agent 列表
{candidates_json}

## 选择标准
1. 技能匹配：Agent 必须有所需技能
2. 状态优先：IDLE > BUSY
3. 项目相关性：项目名与任务相关的优先
4. 负载均衡：同等条件选任务少的

## 输出格式
返回 JSON：
{{"selected_agent_id": "xxx", "reason": "选择理由", "confidence": 0.8}}
"""


class LLMRouter:
    """LLM-based routing decision."""

    def __init__(self):
        self.enabled = config.llm_enabled
        self.provider = config.llm_provider
        self.api_key = config.dashscope_api_key
        self.model = config.dashscope_model_name
        self.timeout = 5.0

    async def route(
        self,
        task_type: str,
        description: str,
        required_skills: list[str],
        target_project: Optional[str],
        candidates: list[dict],
    ) -> Optional[dict]:
        """Make routing decision with LLM."""
        if not self.enabled:
            return None

        if not candidates:
            return None

        prompt = BRIDGE_ROUTE_PROMPT.format(
            task_type=task_type,
            description=description,
            required_skills=", ".join(required_skills),
            target_project=target_project or "未指定",
            candidates_json=json.dumps(candidates, ensure_ascii=False, indent=2),
        )

        try:
            result = await self._call_llm(prompt)
            decision = json.loads(result)

            if decision.get("confidence", 0) < 0.5:
                return None

            # Find selected agent
            agent_id = decision.get("selected_agent_id")
            for c in candidates:
                if c["agent_id"] == agent_id:
                    return {"agent": c, "reason": decision.get("reason")}

            return None

        except (asyncio.TimeoutError, json.JSONDecodeError, Exception):
            return None

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM API."""
        if self.provider == "qwen":
            url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            body = {
                "model": self.model,
                "input": {"prompt": prompt},
                "parameters": {"result_format": "text"},
            }

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url, headers=headers, json=body, timeout=self.timeout
                )
                data = resp.json()
                return data["output"]["text"]

        raise ValueError(f"Unknown LLM provider: {self.provider}")

    def fallback_route(self, candidates: list[dict]) -> dict:
        """Fallback routing without LLM."""
        # Priority: IDLE > least tasks
        idle = [a for a in candidates if a["status"] == "IDLE"]
        if idle:
            return {"agent": idle[0], "reason": "Fallback: IDLE agent"}

        sorted_agents = sorted(candidates, key=lambda a: a.get("current_tasks", 0))
        return {"agent": sorted_agents[0], "reason": "Fallback: least tasks"}


llm_router = LLMRouter()
```

- [ ] **Step 2: Commit**

```bash
git add backend/llm_router.py
git commit -m "feat(backend): add LLM router for intelligent task routing"
```

---

### Task 5.2: 在 TaskManager 中使用 LLM Router

**Files:**
- Modify: `backend/task_manager.py`

- [ ] **Step 1: 修改 delegate_task 使用 LLM**

```python
# In task_manager.py, update delegate_task

from llm_router import llm_router

async def delegate_task(
    self,
    from_agent: str,
    from_machine: str,
    to_project: str,
    title: str,
    description: str,
) -> dict:
    """Delegate task with LLM routing."""
    candidates = agent_registry.find_by_project(to_project)

    if not candidates:
        return {"type": "delegate_failed", "error": f"没有 Agent 在项目 {to_project}"}

    # Filter offline
    candidates = [a for a in candidates if a["status"] != "OFFLINE"]

    # Try LLM routing
    decision = await llm_router.route(
        task_type="delegate",
        description=f"{title}: {description}",
        required_skills=[],
        target_project=to_project,
        candidates=candidates,
    )

    if decision:
        target_agent = decision["agent"]
    else:
        # Fallback
        decision = llm_router.fallback_route(candidates)
        target_agent = decision["agent"]

    # Create task and notify...
    # (rest of the method unchanged)
```

- [ ] **Step 2: Commit**

```bash
git add backend/task_manager.py
git commit -m "feat(backend): integrate LLM router in task delegation"
```

---

### Task 5.3: 实现 Client LLM Router

**Files:**
- Create: `client/llm_router.py`

- [ ] **Step 1: 编写 Client LLM Router**

```python
"""LLM-based local routing for MCP Proxy."""
import json
import asyncio
from typing import Optional
import httpx

from config import config


LOCAL_ROUTE_PROMPT = """本机收到一个远程任务，需要分配给本机 Agent。

## 任务信息
{task_json}

## 本机 Agent 列表
{local_agents_json}

## 选择标准
1. 项目相关性：项目名匹配的优先
2. 状态优先：IDLE > BUSY
3. 技能匹配：有所需技能的优先

输出 JSON：
{{"selected_agent_id": "xxx", "reason": "选择理由"}}
"""


RESULT_FORMAT_PROMPT = """将以下技术结果格式化为用户友好的摘要。

## 原始结果
{raw_result}

## 任务描述
{task_description}

## 输出要求
- 保留关键信息，省略冗余细节
- 用自然语言描述
- 突出重要发现或问题
- 控制在 200 字以内
"""


class LocalLLMRouter:
    """LLM for local agent selection and result formatting."""

    def __init__(self):
        self.enabled = config.llm_enabled
        self.provider = config.llm_provider
        self.api_key = config.dashscope_api_key
        self.model = config.dashscope_model_name  # Can use qwen-mini for speed
        self.timeout = 3.0

    async def select_local_agent(
        self,
        task: dict,
        local_agents: list[dict],
    ) -> Optional[dict]:
        """Select local agent with LLM."""
        if not self.enabled or not local_agents:
            return None

        prompt = LOCAL_ROUTE_PROMPT.format(
            task_json=json.dumps(task, ensure_ascii=False, indent=2),
            local_agents_json=json.dumps(local_agents, ensure_ascii=False, indent=2),
        )

        try:
            result = await self._call_llm(prompt)
            decision = json.loads(result)
            agent_id = decision.get("selected_agent_id")

            for a in local_agents:
                if a["agent_id"] == agent_id:
                    return a

            return None
        except Exception:
            return None

    async def format_result(self, raw_result: str, task_description: str) -> str:
        """Format technical result for user."""
        if not self.enabled:
            return raw_result

        prompt = RESULT_FORMAT_PROMPT.format(
            raw_result=raw_result[:1000],  # Limit input size
            task_description=task_description,
        )

        try:
            return await self._call_llm(prompt)
        except Exception:
            return raw_result

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM API."""
        if self.provider == "qwen":
            url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            body = {
                "model": self.model,
                "input": {"prompt": prompt},
                "parameters": {"result_format": "text"},
            }

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url, headers=headers, json=body, timeout=self.timeout
                )
                data = resp.json()
                return data["output"]["text"]

        raise ValueError(f"Unknown provider: {self.provider}")

    def fallback_select(self, local_agents: list[dict], task: dict) -> dict:
        """Fallback selection without LLM."""
        # Priority: project match > IDLE
        task_project = task.get("project")

        if task_project:
            matching = [a for a in local_agents if a["project"] == task_project]
            if matching:
                idle = [a for a in matching if a["status"] == "IDLE"]
                return idle[0] if idle else matching[0]

        idle = [a for a in local_agents if a["status"] == "IDLE"]
        return idle[0] if idle else local_agents[0]


local_llm_router = LocalLLMRouter()
```

- [ ] **Step 2: Commit**

```bash
git add client/llm_router.py
git commit -m "feat(client): add local LLM router for agent selection and result formatting"
```

---

## 执行检查清单

每个 Phase 完成后，执行以下验证：

### Phase 1 验证
```bash
# 启动 MCP 代理
cd client
pip install -r requirements.txt
python main.py

# 预期：看到 CLI 表格日志，显示 "Connecting to Bridge..."
```

### Phase 2 验证
```bash
# 启动 Claude Code 连接本地 MCP
claude --mcp-config .mcp.json

# 在 Claude Code 中输入：
> 请使用 agent_register 注册，project="test-project", skills=["gitnexus"]

# 预期：返回 agent_id，CLI 显示 REGISTERED 事件
```

### Phase 3 验证
```bash
# 两个 Claude Code 实例
# 实例 A:
> 请使用 task_delegate 委派任务给 project="test-project"，标题 "测试任务"

# 实例 B:
# 预期：收到 Channel 推送通知
> 请使用 get_pending_tasks 查看任务
> 请使用 task_update 更新状态为 IN_PROGRESS
```

### Phase 4 验证
```bash
# 调用远程技能
> 请使用 remote_skill 调用 gitnexus 的 query 操作，参数 {...}

# 预期：同步返回结果
```

### Phase 5 验证
```bash
# 配置 .env 启用 LLM
LLM_ENABLED=true
DASHSCOPE_API_KEY=your_key

# 委派任务，观察 CLI 显示 LLM_ROUTE 事件
```

---

## 计划完成

计划已保存至 `docs/superpowers/plans/2026-05-02-client-mcp-proxy-plan.md`。

**两种执行方式：**

1. **Subagent-Driven (推荐)** - 我为每个任务派遣独立子代理，任务间进行审查，快速迭代

2. **Inline Execution** - 在当前会话中使用 executing-plans 执行，批量执行带检查点审查

**选择哪种方式？**