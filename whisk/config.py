from pathlib import Path
import yaml
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ValidationError

class ConfigError(Exception):
    """Base exception for configuration errors"""
    pass

class ClientConfigError(ConfigError):
    """Raised when client configuration is invalid"""
    pass

class FastAPIConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    prefix: str = "/v1"

class NatsConfig(BaseModel):
    url: str = "nats://localhost:4222"
    user: str = "playground"
    password: str = "kitchenai_playground"

class ClientConfig(BaseModel):
    id: str

class LLMConfig(BaseModel):
    cloud_api_key: Optional[str] = None

class ChromaConfig(BaseModel):
    path: str = "chroma_db"

class ServerConfig(BaseModel):
    type: Literal["fastapi", "nats", "both"]
    fastapi: Optional[FastAPIConfig] = None
    nats: Optional[NatsConfig] = None

class WhiskConfig(BaseModel):
    server: ServerConfig
    nats: NatsConfig
    client: ClientConfig
    llm: Optional[LLMConfig] = LLMConfig()
    chroma: Optional[ChromaConfig] = ChromaConfig()

    @classmethod
    def from_file(cls, path: str | Path) -> "WhiskConfig":
        """Load config from YAML file"""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    @classmethod
    def from_env(cls) -> "WhiskConfig":
        """Load config from environment variables"""
        import os
        
        client_id = os.getenv("WHISK_CLIENT_ID")
        if not client_id:
            raise ClientConfigError("WHISK_CLIENT_ID environment variable must be set")

        return cls(
            client=ClientConfig(id=client_id),
            nats=NatsConfig(
                url=os.getenv("WHISK_NATS_URL", "nats://localhost:4222"),
                user=os.getenv("WHISK_NATS_USER", "playground"),
                password=os.getenv("WHISK_NATS_PASSWORD", "kitchenai_playground"),
            ),
            server=ServerConfig(
                type="nats",  # Default to NATS-only when using env vars
                nats=NatsConfig(
                    url=os.getenv("WHISK_NATS_URL", "nats://localhost:4222"),
                    user=os.getenv("WHISK_NATS_USER", "playground"),
                    password=os.getenv("WHISK_NATS_PASSWORD", "kitchenai_playground"),
                )
            ),
            chroma=ChromaConfig(
                path=os.getenv("WHISK_CHROMA_PATH", "chroma_db")
            )
        ) 