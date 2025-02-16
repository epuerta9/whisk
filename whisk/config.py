from pathlib import Path
from typing import Optional, Literal
import os
import yaml
from pydantic import BaseModel, Field, validator

class ConfigError(Exception):
    """Base exception for configuration errors"""
    pass

class ClientConfigError(ConfigError):
    """Raised when client configuration is invalid"""
    pass

class ClientConfig(BaseModel):
    id: str

class NatsConfig(BaseModel):
    url: str = "nats://localhost:4222"
    user: Optional[str] = None
    password: Optional[str] = None

class FastAPIConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    prefix: str = "/v1"

class ChromaConfig(BaseModel):
    path: str = "chroma_db"

class ServerConfig(BaseModel):
    type: str = "fastapi"  # "fastapi", "nats", or "both"
    fastapi: Optional[FastAPIConfig] = FastAPIConfig()
    nats: Optional[NatsConfig] = None

    @validator('type')
    def validate_server_type(cls, v):
        if v not in ["fastapi", "nats", "both"]:
            raise ValueError(f"Invalid server type: {v}")
        return v

class WhiskConfig(BaseModel):
    server: ServerConfig = ServerConfig()
    client: Optional[ClientConfig] = None
    nats: Optional[NatsConfig] = None
    llm: Optional[dict] = None
    chroma: ChromaConfig = ChromaConfig()

    @classmethod
    def from_env(cls) -> "WhiskConfig":
        """Load config from environment variables"""
        # Check for required client_id
        client_id = os.getenv("WHISK_CLIENT_ID")
        if not client_id:
            raise ClientConfigError("WHISK_CLIENT_ID environment variable must be set")

        # Build config
        config = cls(
            client=ClientConfig(id=client_id),
            nats=NatsConfig(
                url=os.getenv("WHISK_NATS_URL", "nats://localhost:4222"),
                user=os.getenv("WHISK_NATS_USER"),
                password=os.getenv("WHISK_NATS_PASSWORD")
            ) if any([
                os.getenv("WHISK_NATS_URL"),
                os.getenv("WHISK_NATS_USER"),
                os.getenv("WHISK_NATS_PASSWORD")
            ]) else None
        )

        # Update chroma config if path is set
        if chroma_path := os.getenv("WHISK_CHROMA_PATH"):
            config.chroma.path = chroma_path

        return config

    @classmethod
    def from_file(cls, path: str | Path) -> "WhiskConfig":
        """Load config from YAML file"""
        # Convert string to Path if needed
        if isinstance(path, str):
            path = Path(path)
            
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path) as f:
            config_data = yaml.safe_load(f)
            
        # Ensure chroma config is properly structured
        if "chroma" in config_data and isinstance(config_data["chroma"], str):
            config_data["chroma"] = {"path": config_data["chroma"]}

        return cls(**config_data) 