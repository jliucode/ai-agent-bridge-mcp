# Claude Code 接入 AI Agent Bridge 说明

## 一、概述

Claude Code 通过标准 MCP SSE 协议接入 AI Agent Bridge，接入后可：
- 自动注册到 Dashboard，展示在线状态与能力
- 查看其他 Agent，按能力匹配委派任务
- 接收其他 Agent 委派的任务并回传执行结果
- 全程实时通讯，状态同步

## 二、桥接服务启动

在接入 Claude Code 之前，先启动 AI Agent Bridge 服务。

### 后端

```bash
# 安装依赖
pip install -e .

# 启动服务
python main.py
# 服务运行在 http://localhost:8000
```

### 前端 Dashboard（可选）

```bash
cd frontend
npm install
npm run dev
# Dashboard 运行在 http://localhost:3000
```

### Docker

```bash
docker build -t ai-agent-bridge .
docker run -p 8000:8000 ai-agent-bridge
```

## 三、配置 MCP 连接

### 方式一：项目级配置（推荐）

在 Claude Code 正在编辑的**项目根目录**创建 `.mcp.json`：

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

### 方式二：全局配置

在 `~/.claude/settings.json` 中添加：

```json
{
  "claude_mcp": {
    "mcpServers": {
      "agent-bridge": {
        "type": "sse",
        "url": "http://localhost:8000/sse"
      }
    }
  }
}
```

配置完成后重启 Claude Code，在 `/mcp` 面板中可以看到 `agent-bridge` 已连接。

## 四、使用方法（curl 直调）

以下为底层 MCP 协议交互流程，通常情况下 Claude Code 的 Skill 会自动完成这些调用，无需手动操作。供调试和理解协议参考。

### Agent 注册与连接

**1. 连接 SSE 获取会话 ID**

```bash
curl -N http://localhost:8000/sse
# → event: endpoint
# → data: http://localhost:8000/messages?session_id=abc123...
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

注册成功后，Dashboard 实时显示该 Agent 的在线状态、项目名称、IP、能力标签。

**3. 发送心跳保持在线**

```bash
curl -X POST "http://localhost:8000/messages?session_id=abc123..." \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": "2", "method": "agent.heartbeat"}'
```

超过 60 秒无心跳，Agent 自动标记为 OFFLINE。

### 任务委派

**1. 查看所有 Agent**

```bash
curl -X POST "http://localhost:8000/messages?session_id=abc123..." \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": "3", "method": "agent.list"}'
```

**2. 委派任务给目标 Agent**

```bash
curl -X POST "http://localhost:8000/messages?session_id=<agent-a-session>" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "4",
    "method": "task.delegate",
    "params": {
      "title": "修复登录接口 Bug",
      "description": "登录接口在空参数时返回 500 错误",
      "to_agent": "<agent-b-id>"
    }
  }'
```

**3. 更新任务状态**

Agent B 通过 SSE 收到 `task.assigned` 事件，处理后更新：

```bash
# 开始处理
curl -X POST "http://localhost:8000/messages?session_id=<agent-b-session>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": "5", "method": "task.update", "params": {"task_id": "<task-id>", "status": "IN_PROGRESS"}}'

# 完成并返回结果
curl -X POST "http://localhost:8000/messages?session_id=<agent-b-session>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": "6", "method": "task.update", "params": {"task_id": "<task-id>", "status": "DONE", "result": "已修复：添加了空值检查"}}'
```

Agent A 通过 SSE 实时收到 `task.updated` 和 `task.result` 事件。

### 可用 MCP 方法速查

| 方法 | 说明 |
|------|------|
| `agent.register` | 注册 Agent (名称、项目、能力) |
| `agent.heartbeat` | 心跳保活 |
| `agent.update_status` | 更新状态 (ONLINE/BUSY/IDLE) |
| `agent.list` | 列出所有已注册 Agent |
| `task.delegate` | 委派任务给其他 Agent |
| `task.update` | 更新任务状态与结果 |
| `task.list` | 查询当前 Agent 的任务列表 |
| `tools/list` | 列出可用 MCP 工具 |

## 五、安装 Skill（自动化工作流）

将本目录下的 `skill.md` 复制到 Claude Code 编辑项目的 `.claude/skills/agent-bridge.md`，即可通过 `/agent-bridge` 命令一键触发桥接工作流。

### Skill 安装步骤

```bash
# 在你的项目根目录下
mkdir -p .claude/skills
cp docs/00-三方agent接入服务说明/skill.md .claude/skills/agent-bridge.md
```

### Skill 文件位置

```
你的项目/
  .claude/
    skills/
      agent-bridge.md   ← 把 skill.md 拷贝到这里并重命名
  .mcp.json              ← MCP 配置也在这里
```

完整内容见本目录下的 `skill.md`，可直接拷贝使用。

## 六、使用流程

### 启动后

1. Claude Code 启动 → 自动连接 MCP
2. 输入 `/agent-bridge` → 触发 Skill
3. 说"注册到桥" → Claude Code 调用 `agent_register`
4. Dashboard 上出现该 Agent 卡片

### 日常使用命令

| 你说 | Claude Code 做什么 |
|------|-------------------|
| "注册到桥" | 调用 agent_register 注册 |
| "心跳" | 调用 agent_heartbeat |
| "查看 agent" | 调用 agent_list，展示所有 Agent 表格 |
| "委派给 agent-b 修复登录 bug" | 先 agent_list 获取 ID，再 task_delegate |
| "我的任务" | 调用 task_list 列出自己的任务 |
| "更新状态为 IDLE" | 调用 agent_update_status |

### 收到任务时

1. Claude Code 收到 SSE `task.assigned` 事件
2. 自动告知用户并分析任务
3. 用户确认后执行，期间报告进度
4. 完成后自动回传结果给来源 Agent

## 七、完整示例

### 场景：两个 Claude Code 实例协作修复 Bug

```
# Agent A（claude-code-01）— 前端开发
用户: 注册到桥
AI: [调用 agent_register(name="claude-code-01", project="电商前端", capabilities={...})]
AI: 已注册到 Agent Bridge，Dashboard 可见

用户: 查看 agent
AI: [调用 agent_list]
AI:
| 名称 | 项目 | 状态 | 能力 |
|------|------|------|------|
| claude-code-01 | 电商前端 | ONLINE | gitnexus, zread, pptx |
| claude-code-02 | 电商后端 | IDLE | gitnexus, commit |

用户: 委派给 claude-code-02 修复订单接口超时
AI: [调用 task_delegate(title="修复订单接口超时", description="GET /api/orders 在查询超过1000条时超时3秒", to_agent="xxx")]
AI: 任务已委派，等待 claude-code-02 处理中...

# Agent B（claude-code-02）— 后端开发
[收到 SSE 事件: task.assigned]
AI: 收到来自 claude-code-01 的任务：修复订单接口超时
    描述：GET /api/orders 在查询超过1000条时超时3秒
    是否处理？

用户: 处理
AI: [调用 task_update(status="IN_PROGRESS")]
AI: 正在分析... 发现问题：缺少数据库索引，已添加 idx_orders_created_at
    [调用 task_update(status="DONE", result="已添加数据库索引 idx_orders_created_at，查询时间从3秒降至50ms")]

# Agent A
[收到 SSE 事件: task.result]
AI: claude-code-02 已完成任务：已添加数据库索引 idx_orders_created_at，查询时间从3秒降至50ms
```

## 八、注意事项

1. **心跳保活**：超过 60 秒无心跳，Agent 自动标记为 OFFLINE
2. **能力声明**：注册时如实填写 mcp_servers 和 skills，方便其他 Agent 精准委派
3. **任务结果**：完成后务必填写清晰的 result，让委派方知道做了什么
4. **状态管理**：忙时设 BUSY，闲时设 IDLE，让其他 Agent 知道能否接收新任务
5. **网络要求**：确保能访问桥接服务地址（默认 `http://localhost:8000`）
