"""AI Agent Bridge MCP — Entry Point.

Starts the FastAPI server with uvicorn on port 8000.
"""

import uvicorn

from config import setup_logging


def main():
    setup_logging()
    from backend.server import create_app
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
