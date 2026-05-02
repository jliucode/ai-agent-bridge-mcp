"""Configuration loader for MCP Proxy."""
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel


class Config(BaseModel):
    """MCP Proxy configuration."""
    bridge_url: str = "ws://localhost:8000/ws_proxy"
    log_level: str = "INFO"
    llm_enabled: bool = False
    llm_provider: str = "qwen"
    dashscope_api_key: str = ""
    dashscope_model_name: str = "qwen-max"

    @classmethod
    def load(cls) -> Config:
        """Load configuration from .env file."""
        env_path = Path(__file__).parent / ".env"
        load_dotenv(env_path)

        return cls(
            bridge_url=os.getenv("BRIDGE_URL", "ws://localhost:8000/ws_proxy"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            llm_enabled=os.getenv("LLM_ENABLED", "false").lower() == "true",
            llm_provider=os.getenv("LLM_PROVIDER", "qwen"),
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY", ""),
            dashscope_model_name=os.getenv("DASHSCOPE_MODEL_NAME", "qwen-max"),
        )


config = Config.load()