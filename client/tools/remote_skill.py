"""Remote skill MCP tool."""
import asyncio
import time
import uuid
from mcp.types import Tool, TextContent

from remote_agents_cache import RemoteAgentsCache
from utils.file_transfer import FileTransfer
from utils.logger import logger


REMOTE_SKILL_TOOL = Tool(
    name="remote_skill",
    description="调用远程 Agent 的技能。自动选择合适的 Agent，支持文件传输。",
    inputSchema={
        "type": "object",
        "properties": {
            "skill": {
                "type": "string",
                "description": "技能名称（如 gitnexus, pptx）",
            },
            "action": {
                "type": "string",
                "description": "具体操作（如 query, create）",
            },
            "params": {
                "type": "object",
                "description": "操作参数",
            },
            "to_project": {
                "type": "string",
                "description": "目标项目（可选，用于筛选）",
            },
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "需传输的文件路径（可选）",
            },
        },
        "required": ["skill", "action", "params"],
    },
)

# Global cache and pending results
remote_cache = RemoteAgentsCache()
pending_results: dict[str, asyncio.Future] = {}


async def handle_remote_skill(mcp_server, arguments: dict) -> list:
    """Handle remote_skill tool call."""
    skill = arguments["skill"]
    action = arguments["action"]
    params = arguments["params"]
    to_project = arguments.get("to_project")
    files = arguments.get("files", [])

    # Update cache from agent_manager
    remote_cache.update(mcp_server.agent_manager.remote_agents)

    # Find candidates
    candidates = remote_cache.find_by_skill(skill, to_project)
    if not candidates:
        return [TextContent(type="text", text=f"没有 Agent 提供 {skill} 技能")]

    # Filter out offline agents
    candidates = [a for a in candidates if a["status"] != "OFFLINE"]
    if not candidates:
        return [TextContent(type="text", text=f"所有 {skill} Agent 都离线")]

    # Select target
    local_agent_ids = list(mcp_server.agent_manager.agents.keys())
    target = remote_cache.select_agent(candidates)
    is_local = remote_cache.is_local(target["agent_id"], local_agent_ids)

    # Generate task ID
    task_id = f"skill-{int(time.time())}-{uuid.uuid4().hex[:4]}"

    # Handle files
    file_data = []
    if files and not is_local:
        file_data = FileTransfer.read_files(files)

    # Get source agent
    session_id = getattr(mcp_server.server, 'session_id', 'default')
    source_agent = mcp_server.agent_manager.get_agent_by_session(session_id)

    # Send to Bridge
    await mcp_server.bridge.send({
        "type": "skill_call",
        "task_id": task_id,
        "skill": skill,
        "action": action,
        "params": params,
        "files": file_data,
        "from_agent": source_agent.agent_id if source_agent else "unknown",
        "from_machine": mcp_server.bridge.machine_ip,
        "to_agent": target["agent_id"],
        "to_machine": target["machine_ip"],
        "is_local": is_local,
    })

    logger.log_event("SKILL_CALL", skill, "Calling", f"→ {target['project']}", "🔄")

    # Wait for result (synchronous call)
    future = asyncio.Future()
    pending_results[task_id] = future

    try:
        result = await asyncio.wait_for(future, timeout=120)
        logger.log_event("SKILL_CALL", skill, "Done", f"✅ {target['project']}", "✅")
        return [TextContent(type="text", text=f"远程技能调用结果:\n{result}")]
    except asyncio.TimeoutError:
        logger.log_error(f"技能调用超时: {task_id}")
        return [TextContent(type="text", text=f"调用超时 (120s)")]
    finally:
        pending_results.pop(task_id, None)


async def handle_skill_result(msg: dict):
    """Handle skill result from Bridge."""
    task_id = msg["task_id"]
    result = msg.get("result", "")

    if task_id in pending_results:
        pending_results[task_id].set_result(result)