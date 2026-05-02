# Client-Side MCP Proxy 设计文档

> 日期: 2026-05-02
> 状态: Draft
> 作者: Claude Code (头脑风暴协作)

## 1. 概述

### 1.1 背景

原 AI Agent Bridge MCP 设计存在核心问题：Claude Code 作为按需启动的对话工具，无法实现"自动心跳"、"自动状态切换"等常驻 Agent 功能。

**解决方案：** 在用户机器上部署一个常驻 MCP 代理进程，作为本地 Agent 与远程 Bridge 之间的中介层。

### 1.2 核心理念

```
多台机器上的 Agent 上报自己的功能 → 形成 MCP 功能池子
本地常驻 MCP 服务把这些功能包装成 MCP 技能提供给用户
```

### 1.3 架构概览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Bridge Server (远程)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │ Agent Registry│ │ Task Manager │ │ WebSocket    │ │ LLM Router     │ │
│  │ (已有)        │ │ (已有)       │ │ /ws_proxy(新)│ │ (Phase 5)      │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↑↓ WebSocket
┌─────────────────────────────────────────────────────────────────────────┐
│                        用户机器                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                   MCP 代理 (client/) — 唯一常驻进程                   ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ ││
│  │  │ Bridge Conn  │  │ Agent Registry│  │ Tool Sync   │  │ Channel  │ ││
│  │  │ (WebSocket)  │  │ (本地Agent管理)│  │ (动态tools) │  │ (推送)   │ ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────┘ ││
│  │  ┌──────────────┐  ┌──────────────┐                                  ││
│  │  │ CLI Logger   │  │ LLM Local    │                                  ││
│  │  │ (表格输出)   │  │ (Phase 5)    │                                  ││
│  │  └──────────────┘  └──────────────┘                                  ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                    ↑↓ MCP stdio                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │ Agent A      │  │ Agent B      │  │ Agent C      │                   │
│  │ (project: X) │  │ (project: Y) │  │ (project: Z) │                   │
│  └──────────────┘  └──────────────┘  └──────────────┘                   │
└─────────────────────────────────────────────────────────────────────────┘
```

**核心组件：**

| 组件 | 位置 | 职责 |
|------|------|------|
| Bridge Server | 远程服务器 | 全局 Agent 注册中心、任务路由、WebSocket 推送 |
| MCP 代理 | 用户机器 `client/` | 本地常驻，连接 Bridge、管理本地 Agent、暴露动态 tools |
| Agent | 用户机器各进程 | 调用本地 MCP tools 注册、获取任务、调用远程技能 |

---

## 2. 四步渐进式设计

### Step 1: 托盘应用启动

- 托盘应用启动后只上报机器 IP
- 建立 WebSocket 连接到 Bridge

### Step 2: Agent 自注册

- 该 IP 的机器可以启动多个编程 Agent
- Agent 调用托盘应用的固定 MCP tool `agent_register`
- 各自上报自己在做的项目名称和拥有的技能

### Step 3: 动态 MCP 包装

- 托盘应用同步服务器上各个 Agent 服务
- 包装成动态的 MCP tools

### Step 4: Agent 重载

- Agent 重新加载 MCP 后，获取在线的全部 tools

---

## 3. Phase 1: MCP 代理基础架构

### 3.1 文件结构

```
client/
├── main.py              # 入口：启动 MCP 代理
├── config.py            # 配置加载（.env）
├── bridge_client.py     # WebSocket 连接 Bridge
├── mcp_server.py        # MCP Server 实现（stdio + Channel）
├── logger.py            # CLI 表格日志输出
├── .env                 # 配置文件
└── requirements.txt     # 依赖
```

### 3.2 配置项

```env
BRIDGE_URL=ws://192.168.1.100:8000/ws_proxy
LOCAL_MCP_PORT=9000
LOG_LEVEL=INFO
# LLM 配置（Phase 5 启用）
LLM_ENABLED=true
LLM_PROVIDER=qwen
DASHSCOPE_API_KEY=xxx
DASHSCOPE_MODEL_NAME=qwen-max
```

### 3.3 WebSocket 协议

Bridge 新增 `/ws_proxy` 端点：

```json
// 连接握手
{ "type": "hello", "machine_ip": "192.168.1.50" }

// Bridge 确认
{ "type": "welcome", "machine_id": "machine-192-168-1-50" }

// 心跳（代理每 30s 发送）
{ "type": "machine_heartbeat", "online_agents": [...], "timestamp": ... }

// Bridge 推送任务
{ "type": "task_assigned", "agent_id": "xxx", "task": {...} }

// 代理上报 Agent 注册
{ "type": "agent_register", "agent_id": "xxx", "project": "web-app", "skills": [...] }

// 代理上报 Agent 状态变更
{ "type": "agent_status", "agent_id": "xxx", "status": "BUSY" }
```

### 3.4 CLI 表格日志格式

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
│ 10:26:15    │ TASK        │ #101       │ 🔄 In Progress│ Agent A processing│
│ 10:30:00    │ HEARTBEAT   │ Bridge     │ ✅ OK       │ 30s interval    │
└─────────────┴─────────────┴────────────┴─────────────┴─────────────────┘

Agents Online: 3 │ Tasks Pending: 1 │ Last HB: 10:30:00
```

### 3.5 依赖

```txt
mcp>=1.0.0
websockets>=12.0
rich>=13.0          # 表格输出
python-dotenv>=1.0
```

---

## 4. Phase 2: Agent 注册与心跳

### 4.1 Agent ID 生成规则

```python
# 格式: {project}-{PID}-{short_hash}
# 示例: web-app-12345-a3f2
def generate_agent_id(project: str, pid: int) -> str:
    short_hash = hashlib.md5(f"{project}{pid}{time.time()}".encode()).hexdigest()[:4]
    return f"{project}-{pid}-{short_hash}"
```

### 4.2 MCP Tools 定义

| Tool 名称 | 参数 | 返回值 | 说明 |
|----------|------|--------|------|
| `agent_register` | `project: str`, `skills: list[str]`, `description: str?`, `capabilities: dict?` | `{agent_id, status, pending_tasks}` | Agent 注册/更新信息 |
| `agent_heartbeat` | 无 | `{success, timestamp}` | Agent 手动发送心跳（可选） |
| `agent_update_status` | `status: str` (IDLE/BUSY) | `{success}` | Agent 更新自身状态 |
| `get_pending_tasks` | 无 | `{tasks: list}` | Agent 主动查询待处理任务 |
| `list_remote_agents` | 无 | `{agents: list}` | 查询远程 Agent 列表 |

### 4.3 agent_register 行为

| 调用时机 | 行为 |
|----------|------|
| 首次调用 | 注册新 Agent，生成 agent_id |
| 再次调用 | 更新已有 Agent 信息（可部分更新） |

Agent 可随时显式调用 `agent_register` 上传更多信息和技能。

### 4.4 Agent 存活检测

**主要方案：Session 连接状态检测**

| 方案 | 优先级 | 适用场景 |
|------|--------|----------|
| **Session 连接状态** | Phase 2 实现 | Claude Code（MCP stdio 连接），断开自动 OFFLINE |
| **PID 存活检测** | 备用方案 | 非 Claude Code Agent，或 session 检测失效时 |

```python
class AgentManager:
    def __init__(self):
        self.sessions = {}  # session_id → agent_id

    def on_session_disconnect(self, session_id: str):
        # Session 断开时，对应 Agent 自动 OFFLINE
        agent_id = self.sessions.get(session_id)
        if agent_id:
            self.mark_agent_offline(agent_id)
            del self.sessions[session_id]
```

### 4.5 心跳机制

| 层级 | 心跳机制 |
|------|----------|
| MCP 代理 → Bridge | WebSocket 每 30 秒发送 `machine_heartbeat`（含本机所有在线 Agent 列表） |
| Agent → MCP 代理 | **无心跳**，session 连接状态检测 |
| Bridge | WebSocket 断开 → 该机器所有 Agent OFFLINE |

---

## 5. Phase 3: 任务获取与通知

### 5.1 完整任务流程

```
请求方 Agent → 请求方 MCP代理 → Bridge → 目标 MCP代理 → 目标 Agent
     │              │                │              │            │
     │ MCP stdio    │ WebSocket      │ WebSocket    │ MCP stdio  │
```

### 5.2 MCP Tools（新增）

| Tool | 参数 | 调用方 | 说明 |
|------|------|--------|------|
| `task_delegate` | `project, title, description` | 请求方 Agent | 委派任务给目标项目 |
| `get_pending_tasks` | 无 | 目标 Agent | 查询自己的待处理任务 |
| `task_update` | `task_id, status, result?` | 目标 Agent | 更新任务状态 |
| `list_remote_agents` | 无 | 所有 Agent | 查询远程 Agent 列表 |

### 5.3 Channel 推送格式

MCP 代理收到 `task_assigned` 后，推送给对应 Agent：

```python
await mcp.notification({
    "method": "notifications/claude/channel",
    "params": {
        "content": f"""新任务到达!
任务: {task['title']}
描述: {task['description']}

建议操作:
1. 调用 get_pending_tasks 查看完整任务详情
2. 调用 task_update 开始处理任务""",
        "meta": {
            "source": "agent-bridge",
            "task_id": task_id,
            "type": "task_assigned"
        }
    }
})
```

### 5.4 Channel 限制说明

| Channel 能做到 | Channel 做不到 |
|----------------|---------------|
| ✅ 推送消息到 Agent 终端 | ❌ 强制 Agent 自动调用 tool |
| ✅ Agent 自动看到内容 | ❌ Agent 自动执行操作 |
| ✅ 用户无需刷新/轮询 | ❌ 替代用户指令 |

**实际工作流程：**
1. Channel 推送到达 → Agent 展示给用户（自动）
2. 用户看到消息后输入指令（如 "查看任务详情"）
3. Agent 调用 `get_pending_tasks`
4. 用户继续输入（如 "开始处理"）
5. Agent 调用 `task_update` 并执行任务

### 5.5 任务状态枚举

| 状态 | 说明 |
|------|------|
| `PENDING` | 待处理（已推送，未开始） |
| `IN_PROGRESS` | 处理中 |
| `DONE` | 已完成 |
| `FAILED` | 失败 |

---

## 6. Phase 4: 动态 MCP Tools（远程技能调用）

### 6.1 remote_skill Tool

**方案 3：统一命名 + 参数指定**

```python
remote_skill(
    skill: str,           # 技能名，如 "gitnexus"、"pptx"
    to_project: str?,     # 目标项目名（可选）
    action: str,          # 具体操作
    params: dict,         # 操作参数
    files: list[str]?     # 需传输的文件路径
)
```

### 6.2 同步调用

Agent 调用 `remote_skill`，阻塞等待结果（超时 60-120 秒）：

```
Agent 调用 remote_skill
    ↓
MCP 代理发送请求到 Bridge/目标 MCP代理
    ↓
MCP 代理等待结果
    ↓
MCP 代理返回结果给 Agent
    ↓
Agent 继续执行
```

### 6.3 本机 vs 远程文件处理

| 场景 | 目标 Agent 位置 | 文件处理方式 |
|------|-----------------|--------------|
| **本机调用** | 同一 MCP 代理下的其他 Agent | ✅ 无需传输，直接读取本机路径 |
| **远程调用** | 其他机器的 Agent | ⚠️ MCP代理读取文件 → WebSocket传输 → 远程保存 |

**判断逻辑：**

```python
def is_local_agent(target_agent_id: str) -> bool:
    return target_agent_id in self.local_agents
```

### 6.4 远程文件传输结构

```json
{
    "type": "skill_call",
    "files": [
        {
            "original_path": "/home/user/docs/slide.md",
            "filename": "slide.md",
            "content": "base64_encoded_content...",
            "size": 2048
        }
    ]
}
```

### 6.5 负载均衡选择策略（Phase 4 简单版）

```python
def select_agent(candidates):
    # 优先 IDLE
    idle_agents = [a for a in candidates if self.agents[a]["status"] == "IDLE"]
    if idle_agents:
        return self.agents[idle_agents[0]]

    # 其次最少任务
    sorted_agents = sorted(candidates,
                           key=lambda a: self.agents[a]["current_tasks"])
    return self.agents[sorted_agents[0]]
```

---

## 7. Phase 5: LLM 智能调度

### 7.1 两层 LLM 职责

| 层级 | LLM 职责 | 决策场景 |
|------|---------|----------|
| **Bridge LLM** | 全局路由 | 任务委派选择最佳 Agent、远程技能调用匹配 |
| **MCP 代理 LLM** | 本地优化 | 本机多 Agent 选择、结果格式化、错误诊断 |

### 7.2 Bridge LLM Prompt

```python
BRIDGE_ROUTE_PROMPT = """
你是一个任务路由决策助手。根据以下信息选择最合适的目标 Agent。

## 任务信息
- 类型: {task_type}
- 描述: {description}
- 需要技能: {required_skills}
- 目标项目: {target_project}

## 候选 Agent列表
{candidates_json}

## 选择标准
1. 技能匹配：Agent 必须有所需技能
2. 状态优先：IDLE > BUSY
3. 项目相关性：项目名与任务相关的优先
4. 负载均衡：同等条件选任务少的

## 输出格式
返回 JSON：
{
    "selected_agent_id": "xxx",
    "reason": "选择理由（一句话）",
    "confidence": 0.8
}
"""
```

### 7.3 MCP 代理 LLM Prompt

```python
LOCAL_ROUTE_PROMPT = """
本机收到一个远程任务，需要分配给本机 Agent。

## 任务信息
{task_json}

## 本机 Agent列表
{local_agents_json}

## 输出格式
返回 JSON：
{
    "selected_agent_id": "xxx",
    "reason": "选择理由"
}
"""

RESULT_FORMAT_PROMPT = """
将以下技术结果格式化为用户友好的摘要。

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
```

### 7.4 失败降级策略

| 场景 | 降级方案 |
|------|----------|
| LLM 调用超时（>5秒） | 使用负载均衡策略 |
| LLM 返回无效 JSON | 使用负载均衡策略 |
| LLM API 错误 | 使用负载均衡策略 |
| LLM 未启用 | 直接使用负载均衡策略 |

### 7.5 LLM 调用成本控制

| 控制方式 | 说明 |
|----------|------|
| 超时限制 | Bridge 5秒，MCP 代理 3秒 |
| 缓存结果 | 相似任务缓存路由决策（1小时内） |
| 置信度阈值 | confidence < 0.5 时降级 |
| 模型分级 | Bridge 用 qwen-max，MCP 代理可用 qwen-mini |

---

## 8. WebSocket 消息类型汇总

| 方向 | 消息类型 | 说明 |
|------|----------|------|
| 代理 → Bridge | `hello` | 连接握手 |
| Bridge → 代理 | `welcome` | 确认连接 |
| 代理 → Bridge | `machine_heartbeat` | 每 30 秒心跳 |
| 代理 → Bridge | `agent_register` | Agent 注册/更新 |
| 代理 → Bridge | `task_delegate` | 请求方委派任务 |
| 代理 → Bridge | `task_update` | 目标方更新任务状态 |
| Bridge → 代理 | `agents_sync` | 同步远程 Agent 列表 |
| Bridge → 代理 | `task_assigned` | 推送新任务 |
| Bridge → 代理 | `task_result` | 任务完成结果 |

---

## 9. 实现顺序

| Phase | 目标 | 关键交付物 |
|-------|------|------------|
| **Phase 1** | 基础架构 | CLI 启动、WebSocket 连接、表格日志 |
| **Phase 2** | Agent 注册 | `agent_register` tool、session 存活检测 |
| **Phase 3** | 任务通知 | `task_delegate`、Channel 推送、`task_update` |
| **Phase 4** | 动态 tools | `remote_skill`、文件传输、本机/远程区分 |
| **Phase 5** | LLM 智能 | Bridge LLM 路由、MCP 代理 LLM 优化 |

---

## 10. 技术要点备忘

### 10.1 Channel 实现

- Capability declaration: `experimental: { 'claude/channel': {} }`
- Notification format: `notifications/claude/channel`
- 启动命令: `claude --dangerously-load-development-channels server:xxx`

### 10.2 PID 检测备用方案

日后如需实现 PID 检测：

```python
async def pid_check_loop(self):
    while True:
        for agent_id, info in self.agents.items():
            if not psutil.pid_exists(info["pid"]):
                self.mark_offline(agent_id)
        await asyncio.sleep(60)
```

---

## 11. 下一步

进入 `superpowers:writing-plans` 技能，生成详细实现计划。