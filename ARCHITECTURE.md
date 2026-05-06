# AI Agent Bridge MCP - Technical Architecture

> Version: 1.0.0
> Updated: 2026-05-02

## 1. Overview

### 1.1 Background

The original AI Agent Bridge MCP design had a core issue: Claude Code runs as an on-demand conversation tool, making it impossible to implement "automatic heartbeat" or "automatic status switching" as persistent Agent features. When users don't send messages → Claude Code doesn't run, unable to maintain long-lived SSE event listening.

### 1.2 Solution

Introducing **Client-Side MCP Proxy (Local MCP Proxy)** as a persistent process to solve:

| Problem | Solution |
|---------|----------|
| Claude Code can't auto-heartbeat | MCP Proxy runs as persistent process, auto-sends heartbeats |
| Can't receive real-time task push | MCP Proxy maintains WebSocket connection, pushes via Channel to Agent |
| Can't share capabilities across machines | MCP Proxy syncs remote Agents, wraps as dynamic MCP tools |

### 1.3 Core Philosophy

```
Agents on multiple machines report their capabilities → forms an MCP capability pool
Local persistent MCP service wraps these capabilities as MCP skills for users
```

---

## 2. Overall Architecture

### 2.1 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Bridge Server (Remote)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │ Agent Registry│ │ Task Manager │ │ WebSocket    │ │ LLM Router     │ │
│  │              │ │              │ │ /ws_proxy    │ │ (Smart Routing)│ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘ │
│         │                 │                │                 │          │
│         └─────────────────┴────────────────┴─────────────────┘          │
│                           Global Coordination Layer                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↑↓ WebSocket
                                    ↑↓ JSON-RPC Messages
┌─────────────────────────────────────────────────────────────────────────┐
│                           User Machine A                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                   MCP Proxy (client/) — Only Persistent Process      ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ ││
│  │  │ Bridge Conn  │  │ Agent Registry│  │ Tool Sync   │  │ Channel  │ ││
│  │  │ (WebSocket)  │  │ (Local Agent) │  │ (Dynamic)   │  │ (Push)   │ ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────┘ ││
│  │  ┌──────────────┐  ┌──────────────┐                                  ││
│  │  │ CLI Logger   │  │ LLM Local    │                                  ││
│  │  │ (Table Log)  │  │ (Local Opt)  │                                  ││
│  │  └──────────────┘  └──────────────┘                                  ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                    ↑↓ MCP stdio                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │ Agent A      │  │ Agent B      │  │ Agent C      │                   │
│  │ (project: X) │  │ (project: Y) │  │ (project: Z) │                   │
│  └──────────────┘  └──────────────┘  └──────────────┘                   │
└─────────────────────────────────────────────────────────────────────────┘

                                    ↑↓ WebSocket
┌─────────────────────────────────────────────────────────────────────────┐
│                           User Machine B                                 │
│  │ MCP Proxy │ ←→ │ Agent D │ │ Agent E │                                │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Four-Step Progressive Design

```
Step 1: Tray App Startup
├── MCP Proxy starts
├── Reports machine IP
├── Establishes WebSocket connection

Step 2: Agent Self-Registration
├── Agent calls agent_register tool
├── MCP Proxy generates unique ID (project-PID-hash)
├── Reports project name + skill list
├── Bridge registration success

Step 3: Dynamic MCP Wrapping
├── MCP Proxy syncs Bridge's Agent list
├── Wraps as remote_skill tool
├── Agent can call remote skills

Step 4: Agent Reload
├── Agent reloads MCP
├── Gets all online tools
├── Capability pool sharing complete
```

---

## 3. Module Architecture

### 3.1 Client Module Architecture

```
client/
├── main.py                 # Entry: Start MCP Proxy
├── config.py               # Config loader (.env)
├── bridge_client.py        # WebSocket connection to Bridge
├── mcp_server.py           # MCP Server (stdio + Channel)
├── agent_manager.py        # Local Agent manager
├── remote_agents_cache.py  # Remote Agent cache
├── llm_router.py           # LLM routing decision
├── tools/
│   ├── __init__.py
│   ├── agent_tools.py      # agent_register, get_pending_tasks
│   ├── task_tools.py       # task_delegate, task_update
│   └── remote_skill.py     # remote_skill
├── utils/
│   ├── __init__.py
│   ├── logger.py           # CLI table logging
│   ├── file_transfer.py    # File transfer utilities
├── .env.example            # Config example
└── requirements.txt        # Dependencies
```

### 3.2 Backend Module Architecture

```
backend/
├── server.py               # FastAPI app entry
├── websocket_handler.py    # WebSocket /ws_proxy endpoint
├── agent_registry.py       # Agent registry center
├── task_manager.py         # Task lifecycle management
├── llm_router.py           # LLM smart routing
├── models.py               # Pydantic data models
├── routes.py               # REST API routes
├── mcp_handler.py          # MCP JSON-RPC handler
```

### 3.3 Module Responsibilities

| Module | Location | Responsibility |
|--------|----------|----------------|
| **Bridge Server** | Remote server | Global Agent registry, task routing, WebSocket push |
| **MCP Proxy** | User machine | Local persistent process, connects Bridge, manages local Agents, exposes dynamic tools |
| **Agent** | User machine processes | Calls local MCP tools to register, get tasks, call remote skills |

---

## 4. Data Flow

### 4.1 Agent Registration Flow

```
Agent                    MCP Proxy                  Bridge
  │                         │                        │
  │── MCP stdio connect ───→│                        │
  │                         │                        │
  │── agent_register() ────→│                        │
  │  (project, skills)      │                        │
  │                         │── generate agent_id ─→ │
  │                         │  (project-PID-hash)    │
  │                         │                        │
  │                         │── WebSocket ─────────→│
  │                         │  {type:agent_register} │
  │                         │                        │
  │                         │                        │── Register to Registry
  │                         │                        │── Return pending_tasks
  │                         │                        │
  │                         │←── WebSocket ─────────│
  │                         │  {type:agent_registered}│
  │                         │                        │
  │←── Return result ───────│                        │
  │  {agent_id, status}     │                        │
```

### 4.2 Task Delegation Flow

```
Requester Agent         Requester MCP Proxy        Bridge           Target MCP Proxy        Target Agent
     │                        │                     │                     │                    │
     │── task_delegate() ───→│                     │                     │                    │
     │  (project, title, desc)│                     │                     │                    │
     │                        │                     │                     │                    │
     │                        │── WebSocket ──────→│                     │                    │
     │                        │ {type:task_delegate}│                     │                    │
     │                        │                     │                     │                    │
     │                        │                     │── LLM routing ────│                    │
     │                        │                     │   (find best Agent)│                    │
     │                        │                     │                     │                    │
     │                        │                     │── WebSocket ──────→│                    │
     │                        │                     │ {type:task_assigned}│                    │
     │                        │                     │                     │                    │
     │                        │                     │                     │── Channel push ──→│
     │                        │                     │                     │                    │
     │                        │                     │                     │                    │← Receive notice
     │                        │                     │                     │                    │
     │                        │                     │                     │                    │── get_pending_tasks
     │                        │                     │                     │←──────────────────│
     │                        │                     │                     │── Return details ─→│
     │                        │                     │                     │                    │
     │                        │                     │                     │                    │── Process task
     │                        │                     │                     │                    │── task_update
     │                        │                     │                     │←──────────────────│
     │                        │                     │                     │── WebSocket ────→│
     │                        │                     │←────────────────────│                    │
     │                        │                     │ {type:task_updated} │                    │
     │                        │                     │                     │                    │
     │                        │←── WebSocket ──────│                     │                    │
     │←── Channel push result │                     │                     │                    │
```

### 4.3 Remote Skill Call Flow

```
Requester Agent          MCP Proxy                  Bridge              Target MCP Proxy
     │                        │                        │                    │
     │── remote_skill() ────→│                        │                    │
     │  (skill, action, params,│                       │                    │
     │   files?)              │                        │                    │
     │                        │                        │                    │
     │                        │── Find candidate ────→│                    │
     │                        │  (skill + project)     │                    │
     │                        │                        │                    │
     │                        │── Determine location ─│                    │
     │                        │  Local? Remote?        │                    │
     │                        │                        │                    │
     │                        │                        │                    │
     │                        │  【Local Agent】       │                    │
     │                        │── Direct MCP stdio ──→│                    │
     │                        │                        │                    │
     │                        │  【Remote Agent】      │                    │
     │                        │── Read files(base64) ─│                    │
     │                        │── WebSocket ─────────→│                    │
     │                        │ {type:skill_call,      │                    │
     │                        │  files:[...]}          │                    │
     │                        │                        │── Forward ───────→│
     │                        │                        │                    │── Save files
     │                        │                        │                    │── Push to Agent
     │                        │                        │                    │── Execute skill
     │                        │                        │                    │── Return result
     │                        │                        │←──────────────────│
     │                        │←──────────────────────│                    │
     │←── Sync return result ─│                        │                    │
```

---

## 5. Protocol Specification

### 5.1 WebSocket Message Types

Message format for Bridge `/ws_proxy` endpoint:

#### Client → Bridge

| Message Type | Description | Structure |
|--------------|-------------|-----------|
| `hello` | Connection handshake | `{type, machine_ip}` |
| `machine_heartbeat` | Every 30s heartbeat | `{type, machine_ip, online_agents, timestamp}` |
| `agent_register` | Agent registration | `{type, agent_id, machine_ip, project, skills, description, capabilities}` |
| `task_delegate` | Task delegation | `{type, from_agent, from_machine, to_project, title, description}` |
| `task_update` | Task update | `{type, task_id, status, result}` |
| `skill_call` | Remote skill call | `{type, task_id, skill, action, params, files, from_agent, to_agent, ...}` |
| `skill_result` | Skill result | `{type, task_id, result, status}` |

#### Bridge → Client

| Message Type | Description | Structure |
|--------------|-------------|-----------|
| `welcome` | Connection confirmation | `{type, machine_id, timestamp}` |
| `agent_registered` | Registration success | `{type, agent_id, pending_tasks}` |
| `agents_sync` | Agent sync | `{type, agents: [...], timestamp}` |
| `task_assigned` | Task assignment | `{type, agent_id, task: {...}}` |
| `task_result` | Task result | `{type, task_id, status, result}` |
| `skill_call` | Skill call forward | `{type, task_id, skill, action, params, files, ...}` |
| `skill_result` | Skill result forward | `{type, task_id, result, status}` |

### 5.2 MCP Tools Specification

#### Agent Tools

| Tool | Parameters | Returns | Description |
|------|------------|---------|-------------|
| `agent_register` | `project`, `skills`, `description?`, `capabilities?` | `{agent_id, status, pending_tasks}` | Register/update Agent info, can be called anytime to supplement |
| `get_pending_tasks` | None | `{tasks: [...]}` | Query pending tasks for current Agent |
| `list_remote_agents` | None | `{agents: [...]}` | Query remote Agent list |

#### Task Tools

| Tool | Parameters | Returns | Description |
|------|------------|---------|-------------|
| `task_delegate` | `to_project`, `title`, `description` | `{task_id, target_agent}` | Delegate task to target project |
| `task_update` | `task_id`, `status`, `result?` | `{success}` | Update task status |

#### Remote Skill Tool

| Tool | Parameters | Returns | Description |
|------|------------|---------|-------------|
| `remote_skill` | `skill`, `action`, `params`, `to_project?`, `files?` | `{result}` | Sync call remote Agent's skill |

### 5.3 Channel Push Format

MCP Proxy pushes task notifications via `notifications/claude/channel`:

```python
await mcp.notification({
    "method": "notifications/claude/channel",
    "params": {
        "content": """New task arrived!
Task: {title}
Description: {description}
From: {from_agent}

Suggested actions:
1. Call get_pending_tasks to view full task details
2. Call task_update(status="IN_PROGRESS") to start processing""",
        "meta": {
            "source": "agent-bridge",
            "task_id": "...",
            "type": "task_assigned"
        }
    }
})
```

---

## 6. Core Mechanisms

### 6.1 Agent ID Generation Rule

```python
# Format: {project}-{PID}-{short_hash}
# Example: web-app-12345-a3f2
def generate_agent_id(project: str, pid: int) -> str:
    short_hash = hashlib.md5(
        f"{project}{pid}{time.time()}".encode()
    ).hexdigest()[:4]
    return f"{project}-{pid}-{short_hash}"
```

**Features:**
- Project name prefix for easy identification
- PID distinguishes multiple processes in same project
- short_hash ensures uniqueness

### 6.2 Liveness Detection Mechanism

| Approach | Priority | Use Case |
|----------|----------|----------|
| **Session connection status** | Phase 2 implementation | Claude Code (MCP stdio connection), auto OFFLINE on disconnect |
| **PID liveness detection** | Backup approach | Non-Claude Code Agents, or when session detection fails |

```python
# Session disconnect detection
def on_session_disconnect(session_id: str):
    agent_id = self.sessions.get(session_id)
    if agent_id:
        self.mark_agent_offline(agent_id)
        del self.sessions[session_id]

# PID detection (backup)
async def pid_check_loop(self):
    while True:
        for agent_id, info in self.agents.items():
            if not psutil.pid_exists(info["pid"]):
                self.mark_offline(agent_id)
        await asyncio.sleep(60)
```

### 6.3 Heartbeat Mechanism

| Level | Heartbeat Mechanism | Interval |
|-------|---------------------|----------|
| MCP Proxy → Bridge | WebSocket `machine_heartbeat` | Every 30 seconds |
| Agent → MCP Proxy | **No heartbeat**, session connection status detection | - |
| Bridge → Agent status timeout | WebSocket disconnect → All OFFLINE | - |

### 6.4 Local vs Remote File Handling

| Scenario | Target Location | File Handling |
|----------|-----------------|---------------|
| **Local call** | Agent under same MCP Proxy | Pass path directly, no content transfer |
| **Remote call** | Agent on other machine | Base64 encode → WebSocket → Remote save |

```python
# Local call
if is_local_agent(target["agent_id"]):
    # Pass local path directly
    params["files"] = files  # Don't read content

# Remote call
else:
    # Read and encode
    file_data = FileTransfer.read_files(files)
    params["files"] = file_data  # Base64 encoded
```

---

## 7. LLM Smart Scheduling

### 7.1 Two-Level LLM Responsibilities

| Level | LLM Responsibility | Decision Scenario |
|-------|--------------------|--------------------|
| **Bridge LLM** | Global routing | Task delegation selects best Agent, remote skill call matching |
| **MCP Proxy LLM** | Local optimization | Local multi-Agent selection, result formatting, error diagnosis |

### 7.2 Bridge LLM Routing Decision

```
Task delegation request
    ↓
Basic filtering (by project/skill)
    ↓
LLM analysis:
  - Task description
  - Skill requirements
  - Candidate Agent list
  - Selection criteria (skill match, status priority, project relevance, load balance)
    ↓
Return selected Agent + reason
    ↓
Failed? → Fallback to load balancing
```

### 7.3 Failure Fallback Strategy

| Scenario | Fallback Approach |
|----------|-------------------|
| LLM call timeout (>5s) | Use load balancing (least tasks) |
| LLM returns invalid JSON | Use load balancing |
| LLM API error | Use load balancing |
| LLM not enabled | Direct load balancing |
| Confidence < 0.5 | Use load balancing |

---

## 8. Configuration Specification

### 8.1 Client Configuration

```env
# Connection config
BRIDGE_URL=ws://192.168.1.100:8000/ws_proxy
LOG_LEVEL=INFO

# LLM config (Phase 5 enabled)
LLM_ENABLED=false
LLM_PROVIDER=qwen
DASHSCOPE_API_KEY=
DASHSCOPE_MODEL_NAME=qwen-max
```

### 8.2 Backend Configuration

```env
# Server config
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# LLM config
LLM_ENABLED=false
LLM_PROVIDER=qwen
DASHSCOPE_API_KEY=
DASHSCOPE_MODEL_NAME=qwen-max
```

---

## 9. Task Status Flow

### 9.1 Task Status Enum

| Status | Description |
|--------|-------------|
| `PENDING` | Pending (pushed, not started) |
| `IN_PROGRESS` | In progress |
| `DONE` | Completed |
| `FAILED` | Failed |

### 9.2 Agent Status Flow

```
Agent start → Connect MCP Proxy → Call agent_register → IDLE
                                              ↓
                              session disconnect → OFFLINE (auto)
                                              ↓
                              Bridge WebSocket disconnect → All OFFLINE
```

---

## 10. API Endpoints

### 10.1 REST API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/agents` | List all Agents |
| GET | `/api/agents/{id}` | Get Agent details |
| GET | `/api/tasks` | List tasks |
| GET | `/api/stats` | Dashboard statistics |

### 10.2 WebSocket

| Path | Description |
|------|-------------|
| `/ws_proxy` | MCP Proxy connection (Phase 1-5 new) |
| `/ws` | Frontend Dashboard real-time push |

### 10.3 SSE

| Path | Description |
|------|-------------|
| `/sse` | Agent SSE connection (original) |

---

## 11. Technical Notes

### 11.1 Channel Implementation

- **Capability declaration**: `experimental: { 'claude/channel': {} }`
- **Notification format**: `notifications/claude/channel`
- **Startup command**: `claude --dangerously-load-development-channels`

### 11.2 Channel Limitations

| Channel Can | Channel Cannot |
|-------------|----------------|
| ✅ Push messages to Agent terminal | ❌ Force Agent to auto-call tool |
| ✅ Agent auto-sees content | ❌ Agent auto-executes actions |
| ✅ User no need to refresh/poll | ❌ Replace user commands |

**Actual workflow:**
1. Channel push arrives → Agent displays to user (auto)
2. User sees message and inputs command (e.g., "view task details")
3. Agent calls `get_pending_tasks`
4. User continues input (e.g., "start processing")
5. Agent calls `task_update` and executes task

---

## 12. Dependencies

### 12.1 Client Dependencies

```txt
mcp>=1.0.0
websockets>=12.0
rich>=13.0
python-dotenv>=1.0
pydantic>=2.0
psutil>=5.9
httpx>=0.25
```

### 12.2 Backend Dependencies

```txt
fastapi>=0.100
uvicorn>=0.23
websockets>=12.0
pydantic>=2.0
httpx>=0.25
```

---

## 13. Future Extensions

### 13.1 PID Detection Implementation

When supporting non-Claude Code Agents, implement PID detection:

```python
async def pid_check_loop(self):
    while True:
        for agent_id, info in self.agents.items():
            if not psutil.pid_exists(info["pid"]):
                self.mark_offline(agent_id)
        await asyncio.sleep(60)
```

### 13.2 More LLM Providers

Currently supports Qwen (DashScope), can extend:
- OpenAI (GPT-4)
- Anthropic (Claude)
- Local models (Ollama)

### 13.3 Security Enhancements

- Agent authentication
- Task signature verification
- Encrypted transmission

---

## Appendix

### A. CLI Table Log Format

```
╭───────────────────────────────────────────────────────────────────────╮
│ MCP Proxy v0.1.0 — Machine: 192.168.1.50                              │
╰───────────────────────────────────────────────────────────────────────╯

┌─────────────┬─────────────┬────────────┬─────────────┬─────────────────┐
│ Time        │ Event       │ Agent/Task │ Status      │ Details         │
├─────────────┼─────────────┼────────────┼─────────────┼─────────────────┤
│ 10:23:01    │ CONNECTED   │ Bridge     │ ✅ Online   │ ws://x.x.x.x    │
│ 10:23:02    │ REGISTERED  │ web-app    │ ✅ IDLE     │ gitnexus, pptx  │
│ 10:25:30    │ TASK        │ #101       │ 📥 Assigned │ fix login bug   │
│ 10:30:00    │ HEARTBEAT   │ Bridge     │ ✅ OK       │ 30s interval    │
└─────────────┴─────────────┴────────────┴─────────────┴─────────────────┘

Agents Online: 3 │ Tasks Pending: 1 │ Last HB: 10:30:00
```

### B. File Transfer Format

```json
{
    "original_path": "/home/user/docs/slide.md",
    "filename": "slide.md",
    "content": "base64_encoded_content...",
    "size": 2048
}
```