# AI Agent Bridge MCP

Bridging AI agents via the MCP protocol — agents can communicate, delegate tasks, monitor each other, and collaborate across projects in real time.

## Features

- **Real-time agent communication** via MCP JSON-RPC 2.0 over SSE
- **Task delegation** between agents with status tracking and result delivery
- **Live dashboard** (Vue 3) showing all agents, their capabilities, online status, and current tasks
- **Agent registry** with heartbeat monitoring and automatic offline detection
- **REST API** for querying agents, tasks, and statistics
- **WebSocket push** for real-time frontend updates

## Architecture

```
Frontend (Vue 3 + Pinia)  ←→  WebSocket / REST API  ←→  FastAPI Backend
                                ↑
Agent A ←→ SSE + JSON-RPC ←→ /sse + /messages ←→ Agent B
```

## Quick Start

### Backend

```bash
# Install dependencies
pip install fastapi uvicorn pydantic

# Start the server
python main.py
# Server running at http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Dev server at http://localhost:3000 (proxies API to :8000)
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/agents` | List all agents |
| GET | `/api/agents/{id}` | Get agent details |
| GET | `/api/tasks` | List tasks (optional `?from_agent=` or `?to_agent=`) |
| GET | `/api/tasks/{id}` | Get task details |
| GET | `/api/stats` | Dashboard statistics |
| GET | `/sse` | SSE endpoint (agent connects here) |
| POST | `/messages?session_id=` | JSON-RPC messages from agents |
| WS | `/ws` | WebSocket for frontend real-time updates |

## MCP Protocol

Agents use **JSON-RPC 2.0 over SSE** (POST to `/messages?session_id=`, receive events via `/sse`):

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

### Example: Agent Registration Flow

```bash
# 1. Connect to SSE
curl -N http://localhost:8000/sse
# → event: session
# → data: {"session_id": "abc123..."}

# 2. Register agent
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

# 3. Delegate a task
curl -X POST "http://localhost:8000/messages?session_id=abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "2",
    "method": "task.delegate",
    "params": {
      "title": "Fix login bug",
      "description": "The login endpoint returns 500",
      "to_agent": "<target-agent-id>"
    }
  }'
```

## Configuration

All settings via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_HOST` | `0.0.0.0` | Bind address |
| `SERVER_PORT` | `8000` | Server port |
| `MOONSHOT_API_KEY` | — | Moonshot LLM API key |
| `DASHSCOPE_API_KEY` | — | DashScope (Qwen) API key |
| `DASHSCOPE_MODEL_NAME` | `qwen-max` | DashScope model name |
| `DEFAULT_OUTPUT_DIR` | `output` | Default output directory |

## Docker

```bash
docker build -t ai-agent-bridge .
docker run -p 8000:8000 ai-agent-bridge
```

## Project Structure

```
ai-agent-bridge-mcp/
  main.py               # Entry point — uvicorn runner
  config.py             # Configuration & logging setup
  Dockerfile            # Docker build
  backend/
    server.py           # FastAPI app, SSE/WS endpoints
    mcp_handler.py      # MCP JSON-RPC 2.0 over SSE
    agent_registry.py   # Agent CRUD, heartbeat, state
    task_manager.py     # Task lifecycle, delegation
    models.py           # Pydantic data models
    routes.py           # REST API routes
  frontend/
    index.html
    package.json
    vite.config.js
    src/
      main.js
      App.vue
      api/index.js
      components/
        AgentDashboard.vue
        AgentCard.vue
        TaskPanel.vue
        CapabilityBadge.vue
        StatusIndicator.vue
        StatsBar.vue
      stores/
        agent.js
        task.js
        websocket.js
      utils/format.js
```
