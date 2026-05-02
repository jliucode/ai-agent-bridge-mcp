"""Agent Manager - manages local agents and task dispatching."""
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from bridge_client import BridgeClient
    from mcp_server import MCPProxyServer


class AgentManager:
    """Manages local agents and handles task assignment."""

    def __init__(self, bridge_client: "BridgeClient"):
        """Initialize AgentManager.

        Args:
            bridge_client: Bridge client for communication
        """
        self.bridge = bridge_client
        self.mcp_server: Optional["MCPProxyServer"] = None
        self.agents: dict[str, dict] = {}  # agent_id -> agent_info

    def set_mcp_server(self, mcp_server: "MCPProxyServer"):
        """Set MCP server reference.

        Args:
            mcp_server: MCP Proxy Server instance
        """
        self.mcp_server = mcp_server

    async def handle_task_assigned(self, msg: dict):
        """Handle task_assigned message from Bridge.

        Args:
            msg: Message containing task assignment info
        """
        # TODO: Implement in Task 2.1
        pass

    async def handle_agents_sync(self, msg: dict):
        """Handle agents_sync message from Bridge.

        Args:
            msg: Message containing agent synchronization info
        """
        # TODO: Implement in Task 2.1
        pass

    async def handle_task_result(self, msg: dict):
        """Handle task_result message from Bridge.

        Args:
            msg: Message containing task result info
        """
        # TODO: Implement in Task 2.1
        pass