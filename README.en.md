# AI Agent Bridge MCP

A bridge for AI agents — real-time communication, task delegation, and status monitoring via the MCP protocol.

## Quick Start

### Backend

```bash
# Install dependencies
pip install -e .

# Start the server
python main.py
# Server running at http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Dev server at http://localhost:3000 (API proxied to :8000)
```

### Docker

```bash
docker build -t ai-agent-bridge .
docker run -p 8000:8000 ai-agent-bridge
```

## Usage

### Agent Registration & Connection

Agents connect via **SSE + JSON-RPC 2.0** protocol:

**1. Connect to SSE to get a session ID**

```bash
curl -N http://localhost:8000/sse
# → event: session
# → data: {"session_id": "abc123..."}
```

**2. Register the agent**

```bash
curl -X POST "http://localhost:8000/messages?session_id=abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "agent.register",
    "params": {
      "name": "claude-code",
      "project": "my-project",
      "capabilities": {
        "mcp_servers": ["gitnexus", "zread"],
        "skills": ["pptx", "commit"],
        "description": "Code generation and bug fixing"
      }
    }
  }'
```

Once registered, the Dashboard will show this agent's status, project, IP, and capability badges in real time.

**3. Send heartbeats to stay online**

```bash
curl -X POST "http://localhost:8000/messages?session_id=abc123..." \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": "2", "method": "agent.heartbeat"}'
```

Agents are auto-marked OFFLINE after 60 seconds without a heartbeat.

### Task Delegation

Agent A can delegate a task to Agent B and receive real-time results:

**1. Delegate a task**

```bash
curl -X POST "http://localhost:8000/messages?session_id=<agent-a-session>" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "3",
    "method": "task.delegate",
    "params": {
      "title": "Fix login bug",
      "description": "Login endpoint returns 500 on null input",
      "to_agent": "<agent-b-id>"
    }
  }'
```

**2. Update task progress and result**

Agent B receives a `task.assigned` event via SSE, then updates the task:

```bash
# Start working
curl -X POST "http://localhost:8000/messages?session_id=<agent-b-session>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": "4", "method": "task.update", "params": {"task_id": "<task-id>", "status": "IN_PROGRESS"}}'

# Complete with result
curl -X POST "http://localhost:8000/messages?session_id=<agent-b-session>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": "5", "method": "task.update", "params": {"task_id": "<task-id>", "status": "DONE", "result": "Fixed: added null check"}}'
```

Agent A receives `task.updated` and `task.result` events via SSE in real time.

### Claude Code Integration

Claude Code connects to this bridge via the standard MCP SSE protocol. Once connected, it appears on the Dashboard and can exchange tasks with other agents.

**1. Configure Claude Code**

Create a `.mcp.json` in your project root (or use the `/mcp` command in Claude Code):

```json
{
  "mcpServers": {
    "agent-bridge": {
      "type": "sse",
      "url": "http://localhost:8000/sse"
    }
  }
}
```

**2. Auto-register after connecting**

Once connected, ask Claude Code:

> Use the agent_register tool to register this agent. Set name to "claude-code-01", project to "my-project", and list your MCP servers and skills under capabilities.

Claude Code calls `agent_register` to register. After registration:
- This Claude Code instance appears on the Dashboard with status, project, and capability badges
- Use `agent_list` to see all online agents
- Use `task_delegate` to send tasks to other agents
- Receive real-time task updates from other agents via SSE

**3. List all agents**

> Use agent_list to show all currently connected agents

**4. Delegate a task to another agent**

> Use task_delegate to send "Fix null pointer in login endpoint" to agent-b (ID: xxx). Description: The login endpoint returns 500 when given null input.

**5. Receive results from other agents**

When the target agent completes the task, Claude Code receives a `task.result` event via SSE and can report it in the conversation.

**6. Send heartbeats**

> Use agent_heartbeat to send a heartbeat

Consider adding heartbeat calls to a cron hook for automatic keep-alive every 30 seconds.

### Web Dashboard

Open `http://localhost:3000` to see:
- **StatsBar**: Total agents, online/busy counts, task statistics
- **AgentDashboard**: Agent cards showing status, project, IP, current task, and MCP/Skill tags
- **TaskPanel**: Live task list with delegation flow and execution status

## Features

- **MCP JSON-RPC 2.0 over SSE** — Real-time bidirectional agent communication
- **Task delegation & tracking** — Cross-agent task dispatch, status sync, result delivery
- **Live Dashboard** — Vue 3 real-time display of agent status, capability matrix, task flow
- **Agent registry** — Heartbeat monitoring, auto-offline detection, state management
- **REST API** — Query agents, tasks, and statistics
- **WebSocket push** — Real-time frontend updates

## Architecture

```
Frontend (Vue 3 + Pinia)  ←→  WebSocket / REST API  ←→  FastAPI Backend
                                ↑
Agent A ←→ SSE + JSON-RPC ←→ /sse + /messages ←→ Agent B
```

## Project Structure

```
ai-agent-bridge-mcp/
  main.py               # Entry point — uvicorn runner
  config.py             # Logging & LLM configuration
  pyproject.toml        # Project metadata & dependencies
  Dockerfile            # Docker build
  backend/
    server.py           # FastAPI app, SSE/WS endpoints
    mcp_handler.py      # MCP JSON-RPC 2.0 over SSE
    agent_registry.py   # Agent CRUD, heartbeat, state
    task_manager.py     # Task lifecycle, delegation
    models.py           # Pydantic data models
    routes.py           # REST API routes
  frontend/
    src/
      App.vue           # Root layout
      api/index.js      # REST + WebSocket client
      components/
        AgentDashboard.vue  # Agent card grid
        AgentCard.vue       # Single agent status card
        TaskPanel.vue       # Task list panel
        CapabilityBadge.vue # MCP/Skill tag badge
        StatusIndicator.vue # Online status dot
        StatsBar.vue        # Summary statistics bar
      stores/           # Pinia state management
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/agents` | List all agents |
| GET | `/api/agents/{id}` | Get agent details |
| GET | `/api/tasks` | List tasks (optional `?from_agent=` `?to_agent=`) |
| GET | `/api/tasks/{id}` | Get task details |
| GET | `/api/stats` | Dashboard statistics |
| GET | `/sse` | SSE endpoint (agent connects here) |
| POST | `/messages?session_id=` | JSON-RPC messages from agents |
| WS | `/ws` | WebSocket for frontend real-time updates |

## MCP Methods

### Agent Methods

| Method | Description |
|--------|-------------|
| `agent.register` | Register with name, project, capabilities |
| `agent.heartbeat` | Periodic keep-alive |
| `agent.update_status` | Change status (ONLINE/BUSY/IDLE) |
| `agent.list` | List all registered agents |

### Task Methods

| Method | Description |
|--------|-------------|
| `task.delegate` | Send a task to another agent |
| `task.update` | Update task status and result |
| `task.list` | List tasks for this agent |

### Standard MCP

| Method | Description |
|--------|-------------|
| `tools/list` | List available MCP tools |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_HOST` | `0.0.0.0` | Bind address |
| `SERVER_PORT` | `8000` | Server port |
| `MOONSHOT_API_KEY` | — | Moonshot LLM API key |
| `DASHSCOPE_API_KEY` | — | DashScope (Qwen) API key |
| `DASHSCOPE_MODEL_NAME` | `qwen-max` | DashScope model name |
| `DEFAULT_OUTPUT_DIR` | `output` | Default output directory |
