# AI Agent Bridge MCP

AI Agent 之间的桥梁，基于 MCP 协议实现 agent 间的实时通讯、任务委派与状态监控。

## 快速启动

### 后端

```bash
# 安装依赖
pip install -e .

# 启动服务
python main.py
# 服务运行在 http://localhost:8000


```
### 双远程提交
```
git push origin
git push github --all
```

### 前端

```bash
cd frontend
npm install
npm run dev
# 开发服务运行在 http://localhost:3000 (API 代理到 :8000)
```

### Docker

```bash
docker build -t ai-agent-bridge .
docker run -p 8000:8000 ai-agent-bridge
```

## 使用说明

### Agent 注册与连接

Agent 通过 **SSE + JSON-RPC 2.0** 协议连接到服务器，流程如下：

**1. 连接 SSE 获取会话 ID**

```bash
curl -N http://localhost:8000/sse
# → event: session
# → data: {"session_id": "abc123..."}
```

**2. 注册 Agent**

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
        "description": "代码生成与 Bug 修复"
      }
    }
  }'
```

注册成功后，前端 Dashboard 会实时显示该 Agent 的在线状态、项目名称、IP、能力标签等信息。

**3. 发送心跳保持在线**

```bash
curl -X POST "http://localhost:8000/messages?session_id=abc123..." \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": "2", "method": "agent.heartbeat"}'
```

超过 60 秒无心跳，Agent 会自动标记为 OFFLINE。

### 任务委派

Agent A 可以将任务委派给 Agent B，并实时接收执行结果：

**1. 委派任务**

```bash
curl -X POST "http://localhost:8000/messages?session_id=<agent-a-session>" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "3",
    "method": "task.delegate",
    "params": {
      "title": "修复登录接口 Bug",
      "description": "登录接口在空参数时返回 500 错误",
      "to_agent": "<agent-b-id>"
    }
  }'
```

**2. 更新任务状态**

Agent B 通过 SSE 收到 `task.assigned` 事件，处理后更新状态：

```bash
# 开始处理
curl -X POST "http://localhost:8000/messages?session_id=<agent-b-session>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": "4", "method": "task.update", "params": {"task_id": "<task-id>", "status": "IN_PROGRESS"}}'

# 完成任务并返回结果
curl -X POST "http://localhost:8000/messages?session_id=<agent-b-session>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": "5", "method": "task.update", "params": {"task_id": "<task-id>", "status": "DONE", "result": "已修复：添加了空值检查"}}'
```

Agent A 会通过 SSE 实时收到 `task.updated` 和 `task.result` 事件。

### Claude Code 接入

Claude Code 可以通过标准 MCP SSE 协议接入本桥接服务，接入后自动出现在 Dashboard 上，并可与其他 Agent 互派任务。

**1. 配置 Claude Code**

在项目根目录创建 `.mcp.json`（或通过 `/mcp` 命令在 Claude Code 中配置）：

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

**2. 启动后自动注册**

Claude Code 连接到桥接服务后，在对话中输入：

> 请使用 agent_register 工具注册当前 agent，name 填 "claude-code-01"，project 填 "my-project"，capabilities 中列出你的 MCP 和 skill

Claude Code 会调用 `agent_register` 工具完成注册。注册成功后：
- Dashboard 上出现该 Claude Code 实例的卡片，显示在线状态、项目名、能力标签
- 可以通过 `agent_list` 查看所有在线的 Agent
- 可以通过 `task_delegate` 将任务委派给其他 Agent
- 收到其他 Agent 委派的任务时，会通过 SSE 实时推送

**3. 查看所有 Agent**

> 请使用 agent_list 查看当前在线的所有 agent

**4. 委派任务给其他 Agent**

> 请使用 task_delegate 将「修复登录接口的空指针异常」委派给 agent-b（ID: xxx），描述：用户传空参数时 login 接口返回 500

**5. 接收其他 Agent 的结果**

当目标 Agent 完成任务后，Claude Code 会通过 SSE 收到 `task.result` 事件，可以在对话中查看。

**6. 手动发送心跳**

> 请使用 agent_heartbeat 发送心跳

也可以将心跳添加到 Claude Code 的定时任务或 hook 中，每 30 秒自动发送。

### 网页 Dashboard

打开 `http://localhost:3000`，可以看到：
- **StatsBar**：Agent 总数、在线数、忙闲数、任务统计
- **AgentDashboard**：所有 Agent 卡片，展示状态、项目、IP、当前任务、MCP/Skill 能力标签
- **TaskPanel**：任务列表，实时显示委派关系和执行状态

## 核心功能

- **MCP JSON-RPC 2.0 over SSE** — Agent 实时双向通讯
- **任务委派与追踪** — 跨 Agent 任务分发、状态同步、结果回传
- **炫酷 Dashboard** — Vue 3 实时展示 Agent 状态、能力矩阵、任务流转
- **Agent 注册中心** — 心跳检测、自动离线标记、状态管理
- **REST API** — 查询 Agent、任务、统计数据
- **WebSocket 推送** — 前端实时更新

## 架构

```
Frontend (Vue 3 + Pinia)  ←→  WebSocket / REST API  ←→  FastAPI Backend
                                ↑
Agent A ←→ SSE + JSON-RPC ←→ /sse + /messages ←→ Agent B
```

## 项目结构

```
ai-agent-bridge-mcp/
  main.py               # 入口 — 启动 uvicorn
  config.py             # 日志 & LLM 配置
  pyproject.toml        # 项目元数据与依赖
  Dockerfile            # Docker 构建
  backend/
    server.py           # FastAPI 应用, SSE/WS 端点
    mcp_handler.py      # MCP JSON-RPC 2.0 over SSE
    agent_registry.py   # Agent 注册、心跳、状态
    task_manager.py     # 任务生命周期管理
    models.py           # Pydantic 数据模型
    routes.py           # REST API 路由
  frontend/
    src/
      App.vue           # 根布局
      api/index.js      # REST + WebSocket 客户端
      components/
        AgentDashboard.vue  # Agent 卡片网格
        AgentCard.vue       # 单个 Agent 状态卡片
        TaskPanel.vue       # 任务列表面板
        CapabilityBadge.vue # MCP/Skill 标签
        StatusIndicator.vue # 在线状态指示灯
        StatsBar.vue        # 统计摘要栏
      stores/           # Pinia 状态管理
```

## API 端点

| Method | Path | 说明 |
|--------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/api/agents` | 列出所有 Agent |
| GET | `/api/agents/{id}` | 获取 Agent 详情 |
| GET | `/api/tasks` | 列出任务 (可选 `?from_agent=` `?to_agent=`) |
| GET | `/api/tasks/{id}` | 获取任务详情 |
| GET | `/api/stats` | Dashboard 统计数据 |
| GET | `/sse` | SSE 端点 (Agent 连接) |
| POST | `/messages?session_id=` | Agent JSON-RPC 消息 |
| WS | `/ws` | 前端 WebSocket 实时推送 |

## MCP 协议方法

### Agent 方法

| Method | 说明 |
|--------|------|
| `agent.register` | 注册 Agent (名称、项目、能力) |
| `agent.heartbeat` | 心跳保活 |
| `agent.update_status` | 更新状态 (ONLINE/BUSY/IDLE) |
| `agent.list` | 列出所有已注册 Agent |

### 任务方法

| Method | 说明 |
|--------|------|
| `task.delegate` | 委派任务给其他 Agent |
| `task.update` | 更新任务状态与结果 |
| `task.list` | 查询当前 Agent 的任务列表 |

### 标准 MCP

| Method | 说明 |
|--------|------|
| `tools/list` | 列出可用 MCP 工具 |

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SERVER_HOST` | `0.0.0.0` | 绑定地址 |
| `SERVER_PORT` | `8000` | 服务端口 |
| `MOONSHOT_API_KEY` | — | Moonshot LLM API Key |
| `DASHSCOPE_API_KEY` | — | 百炼 (Qwen) API Key |
| `DASHSCOPE_MODEL_NAME` | `qwen-max` | 百炼模型名 |
| `DEFAULT_OUTPUT_DIR` | `output` | 默认输出目录 |
