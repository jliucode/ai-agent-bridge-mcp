"""MCP Proxy entry point."""
import asyncio
import socket
import sys
from pathlib import Path

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from bridge_client import BridgeClient
from mcp_server import MCPProxyServer
from agent_manager import AgentManager
from utils.logger import logger, ProxyLogger


def get_machine_ip() -> str:
    """Get local machine IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


async def main():
    """Main entry point."""
    machine_ip = get_machine_ip()

    # Initialize logger
    global logger
    logger = ProxyLogger(machine_ip)
    logger.print_header()

    # Initialize components
    bridge = BridgeClient(machine_ip)
    agent_manager = AgentManager(bridge)
    mcp_server = MCPProxyServer(bridge, agent_manager)
    agent_manager.set_mcp_server(mcp_server)

    # Register Bridge message handlers
    bridge.on_message("task_assigned", agent_manager.handle_task_assigned)
    bridge.on_message("agents_sync", agent_manager.handle_agents_sync)
    bridge.on_message("task_result", agent_manager.handle_task_result)

    # Connect to Bridge
    await bridge.connect()

    # Run MCP server and receive loop concurrently
    try:
        await asyncio.gather(
            mcp_server.run(),
            bridge.receive_loop(),
        )
    except KeyboardInterrupt:
        logger.log_event("SHUTDOWN", "System", "Stopped", "User interrupt", "⏹️")
        await bridge.close()


if __name__ == "__main__":
    asyncio.run(main())