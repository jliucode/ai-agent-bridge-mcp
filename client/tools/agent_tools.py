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
    session_id = getattr(mcp_server.server, 'session_id', 'default')

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
    session_id = getattr(mcp_server.server, 'session_id', 'default')

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