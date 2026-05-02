"""WebSocket client for Bridge Server connection."""
import asyncio
import json
import time
from typing import Callable, Optional
import websockets
from websockets.client import WebSocketClientProtocol

from config import config
from utils.logger import logger


class BridgeClient:
    """WebSocket client connecting to Bridge Server."""

    def __init__(self, machine_ip: str):
        self.machine_ip = machine_ip
        self.ws: Optional[WebSocketClientProtocol] = None
        self.machine_id: Optional[str] = None
        self.connected = False
        self._message_handlers: dict[str, Callable] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None

    def on_message(self, msg_type: str, handler: Callable):
        """Register message handler."""
        self._message_handlers[msg_type] = handler

    async def connect(self):
        """Connect to Bridge Server."""
        try:
            self.ws = await websockets.connect(config.bridge_url)
            self.connected = True

            # Send hello
            await self.send({
                "type": "hello",
                "machine_ip": self.machine_ip,
            })

            logger.log_connected(config.bridge_url)

            # Start heartbeat loop
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        except Exception as e:
            logger.log_error(f"Connection failed: {e}")
            self.connected = False

    async def send(self, msg: dict):
        """Send message to Bridge."""
        if self.ws:
            await self.ws.send(json.dumps(msg))

    async def receive_loop(self):
        """Receive messages from Bridge."""
        if not self.ws:
            return

        try:
            for msg_str in self.ws:
                msg = json.loads(msg_str)
                msg_type = msg.get("type")

                if msg_type == "welcome":
                    self.machine_id = msg.get("machine_id")
                    logger.log_event("WELCOME", "Bridge", "Ready", self.machine_id, "✅")

                elif msg_type in self._message_handlers:
                    await self._message_handlers[msg_type](msg)

        except websockets.ConnectionClosed:
            self.connected = False
            logger.log_error("Connection closed")
        except Exception as e:
            logger.log_error(f"Receive error: {e}")

    async def _heartbeat_loop(self):
        """Send heartbeat every 30 seconds."""
        while self.connected:
            await asyncio.sleep(30)
            if self.connected:
                await self.send({
                    "type": "machine_heartbeat",
                    "machine_ip": self.machine_ip,
                    "timestamp": time.time(),
                })

    async def close(self):
        """Close connection."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self.ws:
            await self.ws.close()
        self.connected = False