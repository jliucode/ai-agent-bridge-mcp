"""Task management MCP tools."""
from mcp.types import Tool, TextContent

from utils.logger import logger


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
    session_id = getattr(mcp_server.server, 'session_id', 'default')
    agent = mcp_server.agent_manager.get_agent_by_session(session_id)

    if not agent:
        return [TextContent(type="text", text="错误: Agent 未注册")]

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
            text=f"任务状态已更新!\n"
                 f"ID: {task_id}\n"
                 f"状态: {status}",
        )
    ]