import typer
import importlib
from typing import Optional
from ..config import load_config, ConfigError, WhiskConfig
from ..router import WhiskRouter, set_kitchen_app

app = typer.Typer()

def import_app(app_path: str):
    """Import KitchenAI app from module path
    
    Format: module.path:app_name
    Example: examples.agents.agent:kitchen
    """
    try:
        module_path, app_name = app_path.split(':')
        module = importlib.import_module(module_path)
        return getattr(module, app_name)
    except ValueError:
        raise ValueError("App path must be in format 'module.path:app_name'")
    except ImportError:
        raise ImportError(f"Could not import module '{module_path}'")
    except AttributeError:
        raise AttributeError(f"Could not find app '{app_name}' in module '{module_path}'")

def get_app_path(cli_app_path: Optional[str], config) -> str:
    """Get app path from CLI argument or config"""
    if cli_app_path:
        return cli_app_path
    if config.server.app_path:
        return config.server.app_path
    raise ConfigError("No app path provided. Use CLI argument or set app_path in config.")

def get_application():
    """Get FastAPI application"""
    import os
    
    config = load_config()
    app_path = os.getenv("WHISK_APP_PATH") or get_app_path(None, config)
    kitchen = import_app(app_path)
    router = WhiskRouter(kitchen, config)
    return router.app

@app.command()
def serve(
    app_path: Optional[str] = typer.Argument(None, help="Path to KitchenAI app (format: module.path:app_name)"),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file"),
    host: Optional[str] = typer.Option(None, "--host", "-h", help="Host to bind to"),
    port: Optional[int] = typer.Option(None, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload on code changes")
):
    """Start the Whisk server
    
    Example: whisk serve examples.agents.agent:kitchen
    """
    import uvicorn
    import os
    
    # Load config from file if provided
    if config:
        config = load_config(config)
    else:
        config = load_config()
    
    # Get app path from CLI or config
    resolved_app_path = get_app_path(app_path, config)
    
    # Override host/port if provided
    if host:
        config.server.fastapi.host = host
    if port:
        config.server.fastapi.port = port

    if reload:
        # Set app path in environment for reload mode
        os.environ["WHISK_APP_PATH"] = resolved_app_path
        
        uvicorn.run(
            "whisk.cli.serve:get_application",
            host=config.server.fastapi.host,
            port=config.server.fastapi.port,
            reload=True,
            reload_dirs=["whisk"],
            factory=True
        )
    else:
        # Create router and run
        kitchen = import_app(resolved_app_path)
        router = WhiskRouter(kitchen, config)
        router.run(
            host=config.server.fastapi.host,
            port=config.server.fastapi.port
        )

if __name__ == "__main__":
    app() 