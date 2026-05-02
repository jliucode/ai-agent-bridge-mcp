"""MCP Server implementation with Channel support."""
import asyncio
from typing import Callable
from mcp.server import Server
from mcp.server.stdio import stdio_server

from config import config


class MCPProxyServer:
    """MCP Server that exposes tools and supports Channel notifications."""

    def __init__(self, bridge_client, agent_manager):
        self.bridge = bridge_client
        self.agent_manager = agent_manager
        self.server = Server(
            {"name": "agent-bridge-proxy", "version": "0.1.0"},
            {
                "capabilities": {
                    "tools": {},
                    "experimental": {"claude/channel": {}},
                },
                "instructions": """
Agent Bridge Proxy - 连接到远程 Bridge，管理本地 Agent。

可用功能：
- agent_register: 注册/更新 Agent 信息
- task_delegate: 委派任务给其他项目
- get_pending_tasks: 查询待处理任务
- task_update: 更新任务状态
- list_remote_agents: 查询远程 Agent列表
- remote_skill: 调用远程 Agent 的技能（Phase 4）

当收到任务通知时，Channel 会推送消息到终端。
""",
            },
        )
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup MCP handlers."""
        @self.server.list_tools()
        async def list_tools():
            from tools.agent_tools import AGENT_TOOLS
            from tools.task_tools import TASK_TOOLS
            return AGENT_TOOLS + TASK_TOOLS

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict):
            return await self._handle_tool_call(name, arguments)

    async def _handle_tool_call(self, name: str, arguments: dict):
        """Handle tool call."""
        from tools.agent_tools import handle_agent_register, handle_get_pending_tasks, handle_list_remote_agents
        from tools.task_tools import handle_task_delegate, handle_task_update

        handlers = {
            "agent_register": handle_agent_register,
            "get_pending_tasks": handle_get_pending_tasks,
            "list_remote_agents": handle_list_remote_agents,
            "task_delegate": handle_task_delegate,
            "task_update": handle_task_update,
        }

        handler = handlers.get(name)
        if handler:
            return await handler(self, arguments)
        else:
            return [{"type": "text", "text": f"Unknown tool: {name}"}]

    async def notify_channel(self, content: str, meta: dict):
        """Push notification via Channel."""
        await self.server.notification({
            "method": "notifications/claude/channel",
            "params": {
                "content": content,
                "meta": meta,
            },
        })

    async def run(self):
        """Run MCP server over stdio."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )