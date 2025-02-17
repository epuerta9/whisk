import typer
import importlib
import uvicorn
import os
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ..config import WhiskConfig, ServerConfig, FastAPIConfig, NatsConfig
from ..router import WhiskRouter
import logging

logger = logging.getLogger(__name__)

def get_application():
    """Factory function for uvicorn"""
    # Get configuration from environment variables
    kitchen_path = os.getenv("WHISK_KITCHEN_PATH")
    config_json = os.getenv("WHISK_CONFIG")
    commands_enabled = os.getenv("WHISK_COMMANDS", "false").lower() == "true"
    
    if not kitchen_path or not config_json:
        raise RuntimeError("Missing required environment variables")
    
    config = WhiskConfig.parse_raw(config_json)
    return create_app(kitchen_path, config, enable_commands=commands_enabled)

def create_app(kitchen_path: str, config: WhiskConfig, enable_commands: bool = False):
    """Create FastAPI application"""
    # Import the kitchen module
    module_path, attr = kitchen_path.split(":")
    kitchen_module = importlib.import_module(module_path)
    kitchen = getattr(kitchen_module, attr)
    
    # Create router without command support
    router = WhiskRouter(kitchen, config, enable_commands=False)
    return router.router

def serve(
    kitchen: str = typer.Option(
        "whisk.examples.app:kitchen",
        "--kitchen", "-k",
        help="App to run"
    ),
    host: str = typer.Option(
        "0.0.0.0",
        "--host",
        help="Host to bind to"
    ),
    port: int = typer.Option(
        8000,
        "--port", "-p",
        help="Port to bind to"
    ),
    nats_url: Optional[str] = typer.Option(
        None,
        "--nats-url",
        help="NATS server URL"
    ),
    nats_user: Optional[str] = typer.Option(
        None,
        "--nats-user",
        help="NATS username"
    ),
    nats_password: Optional[str] = typer.Option(
        None,
        "--nats-password",
        help="NATS password"
    ),
    server_type: str = typer.Option(
        "fastapi",
        "--type", "-t",
        help="Server type to run (fastapi, nats, or both)"
    ),
    reload: bool = typer.Option(
        False,
        "--reload", "-r",
        help="Enable auto-reload on file changes"
    ),
    watch_dirs: Optional[List[str]] = typer.Option(
        None,
        "--watch",
        help="Directories to watch for changes"
    ),
    commands: bool = typer.Option(
        False,  # Default to False and ignore
        "--commands",
        help="Enable chat commands (currently disabled)"
    )
):
    """Start the Whisk server"""
    logger.info(f"Starting server with commands enabled: {commands}")
    
    config = WhiskConfig(
        server=ServerConfig(
            type=server_type,
            fastapi=FastAPIConfig(
                host=host,
                port=port
            ),
            nats=NatsConfig(
                url=nats_url,
                user=nats_user,
                password=nats_password
            ) if nats_url else None
        )
    )

    if server_type in ['fastapi', 'both']:
        if reload:
            # Store configuration in environment variables
            os.environ["WHISK_KITCHEN_PATH"] = kitchen
            os.environ["WHISK_CONFIG"] = config.model_dump_json()
            # Don't set WHISK_COMMANDS
            
            # For reload mode, use factory function
            uvicorn.run(
                "whisk.cli.serve:get_application",
                host=host,
                port=port,
                reload=True,
                reload_dirs=watch_dirs,
                reload_includes=["*.py", "*.yml", "*.yaml"],
                factory=True
            )
        else:
            # For normal mode, create app directly
            app = create_app(kitchen, config, enable_commands=False)
            uvicorn.run(app, host=host, port=port)
    elif server_type == 'nats':
        # Start NATS server
        start_nats_server(config) 