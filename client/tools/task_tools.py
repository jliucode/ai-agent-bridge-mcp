"""Task management MCP tools."""
from mcp.types import Tool, TextContent

from utils.logger import logger


TASK_TOOLS = [
    Tool(
        name="task_delegate",
        description="Delegate task to Agent in other project.",
        inputSchema={
            "type": "object",
            "properties": {
                "to_project": {
                    "type": "string",
                    "description": "Target project name",
                },
                "title": {
                    "type": "string",
                    "description": "Task title",
                },
                "description": {
                    "type": "string",
                    "description": "Task detailed description",
                },
            },
            "required": ["to_project", "title", "description"],
        },
    ),
    Tool(
        name="task_update",
        description="Update task status (IN_PROGRESS, DONE, FAILED).",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID",
                },
                "status": {
                    "type": "string",
                    "enum": ["IN_PROGRESS", "DONE", "FAILED"],
                    "description": "Task status",
                },
                "result": {
                    "type": "string",
                    "description": "Task result or note (optional)",
                },
            },
            "required": ["task_id", "status"],
        },
    ),
]


async def handle_task_delegate(mcp_server, arguments: dict) -> list:
    """Handle task_delegate tool call."""
    session_id = getattr(mcp_server.server, 'session_id', 'default')
    agent = mcp_server.agent_manager.get_agent_by_session(session_id)

    if not agent:
        return [TextContent(type="text", text="Error: Agent not registered")]

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
            text=f"Task delegated!\n"
                 f"Target project: {arguments['to_project']}\n"
                 f"Task: {arguments['title']}\n"
                 f"Waiting for result notification...",
        )
    ]


async def handle_task_update(mcp_server, arguments: dict) -> list:
    """Handle task_update tool call."""
    task_id = arguments["task_id"]
    status = arguments["status"]
    result = arguments.get("result", "")

    await mcp_server.bridge.send({
        "type": "task_update",
        "task_id": task_id,
        "status": status,
        "result": result,
    })

    icon = "🔄" if status == "IN_PROGRESS" else "✅" if status == "DONE" else "❌"
    logger.log_task(task_id, status, result, icon)

    return [
        TextContent(
            type="text",
            text=f"Task status updated!\n"
                 f"ID: {task_id}\n"
                 f"Status: {status}",
        )
    ]