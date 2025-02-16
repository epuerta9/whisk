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
    user: Optional[str] = None
    password: Optional[str] = None

class ClientConfig(BaseModel):
    id: Optional[str] = None

class LLMConfig(BaseModel):
    cloud_api_key: Optional[str] = None

class ChromaConfig(BaseModel):
    path: str = "chroma_db"

class ServerConfig(BaseModel):
    type: str = "fastapi"  # Default to just FastAPI
    fastapi: Optional[FastAPIConfig] = FastAPIConfig()
    nats: Optional[NatsConfig] = None

class WhiskConfig(BaseModel):
    server: ServerConfig = ServerConfig()
    client: Optional[ClientConfig] = None
    nats: Optional[NatsConfig] = None
    llm: Optional[LLMConfig] = LLMConfig()
    chroma: Optional[ChromaConfig] = ChromaConfig()

    @classmethod
    def from_file(cls, path: Path) -> "WhiskConfig":
        """Load config from YAML file"""
        if not path.exists():
            return cls()  # Return default config if file doesn't exist
        
        with open(path) as f:
            data = yaml.safe_load(f)
            return cls(**data)

    @classmethod
    def from_env(cls) -> "WhiskConfig":
        """Load config from environment variables"""
        return cls()  # Return default config 