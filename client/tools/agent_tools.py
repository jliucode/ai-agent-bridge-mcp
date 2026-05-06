"""Agent management MCP tools."""
from mcp.types import Tool, TextContent


AGENT_TOOLS = [
    Tool(
        name="agent_register",
        description="Register or update Agent information. First call generates agent_id, subsequent calls can update info.",
        inputSchema={
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": "Project name",
                },
                "skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Skill list (e.g. gitnexus, pptx, commit)",
                },
                "description": {
                    "type": "string",
                    "description": "Agent description (optional)",
                },
                "capabilities": {
                    "type": "object",
                    "description": "Detailed capabilities (optional, e.g. MCP servers, tools)",
                },
            },
            "required": ["project", "skills"],
        },
    ),
    Tool(
        name="get_pending_tasks",
        description="Query pending tasks list for current Agent.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="list_remote_agents",
        description="Query remote Agent list (Agents on other machines).",
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
            text=f"Agent registered successfully!\n"
                 f"ID: {result['agent_id']}\n"
                 f"Status: {result['status']}\n"
                 f"Pending tasks: {len(result['pending_tasks'])}",
        )
    ]


async def handle_get_pending_tasks(mcp_server, arguments: dict) -> list:
    """Handle get_pending_tasks tool call."""
    session_id = getattr(mcp_server.server, 'session_id', 'default')

    tasks = mcp_server.agent_manager.get_pending_tasks(session_id)

    if not tasks:
        return [TextContent(type="text", text="No pending tasks")]

    lines = ["Pending tasks list:"]
    for task in tasks:
        lines.append(f"- #{task['task_id']}: {task['title']}")
        lines.append(f"  From: {task['from_agent']}")
        lines.append(f"  Description: {task['description']}")

    return [TextContent(type="text", text="\n".join(lines))]


async def handle_list_remote_agents(mcp_server, arguments: dict) -> list:
    """Handle list_remote_agents tool call."""
    agents = mcp_server.agent_manager.remote_agents

    if not agents:
        return [TextContent(type="text", text="No remote Agents")]

    lines = ["Remote Agent list:"]
    for agent in agents:
        status_icon = "✅" if agent["status"] == "IDLE" else "🔄"
        lines.append(f"- {agent['project']} ({agent['agent_id']}) {status_icon}")
        lines.append(f"  Skills: {', '.join(agent['skills'])}")

    return [TextContent(type="text", text="\n".join(lines))]