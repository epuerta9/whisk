import typer
from typing import Optional
from ..config import load_config
from ..router import WhiskRouter
from ..examples.app import kitchen

app = typer.Typer()

def get_application():
    """Get FastAPI application"""
    config = load_config()
    router = WhiskRouter(kitchen, config)
    return router.app

@app.command()
def serve(
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file"),
    host: Optional[str] = typer.Option(None, "--host", "-h", help="Host to bind to"),
    port: Optional[int] = typer.Option(None, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload on code changes")
):
    """Start the Whisk server"""
    import uvicorn
    
    # Load config from file if provided
    if config:
        config = load_config(config)
    else:
        config = load_config()
    
    # Override host/port if provided
    if host:
        config.server.fastapi.host = host
    if port:
        config.server.fastapi.port = port

    if reload:
        uvicorn.run(
            "whisk.cli.serve:get_application",
            host=config.server.fastapi.host,
            port=config.server.fastapi.port,
            reload=True,
            factory=True
        )
    else:
        # Create router and run
        router = WhiskRouter(kitchen, config)
        router.run(
            host=config.server.fastapi.host,
            port=config.server.fastapi.port
        )

if __name__ == "__main__":
    app() 