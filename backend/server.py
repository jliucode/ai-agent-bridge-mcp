"""FastAPI application setup for the AI Agent Bridge."""

import json
import logging

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .mcp_handler import frontend_ws, handle_message, sse_endpoint
from .routes import router
from .websocket_handler import proxy_manager, handle_proxy_message

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="AI Agent Bridge MCP", version="1.0.0")

    # CORS — allow frontend dev server and any agent connections
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── REST API routes ──
    app.include_router(router)

    # ── SSE endpoint for agents ──
    @app.get("/sse")
    async def sse(request: Request):
        return await sse_endpoint(request)

    # ── JSON-RPC messages endpoint for MCP clients ──
    @app.post("/messages")
    async def messages(request: Request):
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(
                {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}},
                status_code=400,
            )
        session_id = request.query_params.get("session_id", "")
        if not session_id:
            return JSONResponse(
                {"jsonrpc": "2.0", "id": body.get("id"), "error": {"code": -32000, "message": "Missing session_id query param"}},
                status_code=400,
            )
        result = await handle_message(session_id, body)
        if result is None:
            # MCP notification — no response body
            return JSONResponse(None, status_code=202)
        return JSONResponse(result)

    # ── WebSocket for frontend ──
    @app.websocket("/ws")
    async def ws(websocket):
        await frontend_ws(websocket)

    # ── WebSocket for MCP Proxy connections ──
    @app.websocket("/ws_proxy")
    async def ws_proxy_endpoint(websocket: WebSocket):
        """WebSocket endpoint for MCP Proxy connections."""
        machine_ip = None
        try:
            await websocket.accept()

            # Wait for hello message
            msg = await websocket.receive_json()
            if msg.get("type") != "hello":
                await websocket.close()
                return

            machine_ip = msg["machine_ip"]
            await proxy_manager.connect(websocket, machine_ip)

            while True:
                msg = await websocket.receive_json()
                await handle_proxy_message(websocket, machine_ip, msg)

        except WebSocketDisconnect:
            if machine_ip:
                await proxy_manager.disconnect(machine_ip)
        except Exception as e:
            if machine_ip:
                await proxy_manager.disconnect(machine_ip)

    return app
