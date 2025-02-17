from pathlib import Path
from typing import Optional, Literal
import os
import yaml
from pydantic import BaseModel, Field, validator, field_validator

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
    client_id: Optional[str] = None

class FastAPIConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    prefix: str = "/v1"

class ChromaConfig(BaseModel):
    path: str = "chroma_db"

class ServerConfig(BaseModel):
    type: Literal["fastapi", "nats", "both"]
    fastapi: Optional[FastAPIConfig] = None
    nats: Optional[NatsConfig] = None
    app_path: Optional[str] = None

    @field_validator("type")
    def validate_type(cls, v):
        if v not in ["fastapi", "nats", "both"]:
            raise ValueError("Server type must be either 'fastapi', 'nats', or 'both'")
        return v

    @field_validator("fastapi")
    def validate_fastapi(cls, v, values):
        if values.data.get("type") in ["fastapi", "both"] and v is None:
            return FastAPIConfig()
        return v

    @field_validator("nats")
    def validate_nats(cls, v, values):
        if values.data.get("type") in ["nats", "both"] and v is None:
            return NatsConfig()
        return v

class WhiskConfig(BaseModel):
    server: ServerConfig = ServerConfig(type="fastapi")
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

def load_config(config_path: Optional[str] = None) -> WhiskConfig:
    """Load configuration from file or return default config"""
    if config_path:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(path) as f:
            config_dict = yaml.safe_load(f)
            return WhiskConfig(**config_dict)
    
    # Return default config if no file provided
    return WhiskConfig(
        server=ServerConfig(
            type="fastapi",
            fastapi=FastAPIConfig()
        )
    ) 