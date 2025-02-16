import typer
import importlib
import asyncio
from pathlib import Path
from typing import Optional, List
from watchfiles import awatch
from ..config import WhiskConfig, NatsConfig
from ..client import WhiskClient

app = typer.Typer(help="Development server commands")

@app.command()
def main(
    ctx: typer.Context,
    kitchen: str = typer.Argument(
        "whisk.examples.app:kitchen",
        help="App to run"
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file"
    ),
    workers: int = typer.Option(
        1,
        "--workers",
        "-w",
        help="Number of worker processes"
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        "-r",
        help="Enable auto-reload on file changes"
    ),
    watch_dirs: List[Path] = typer.Option(
        ["./"],
        "--watch",
        help="Directories to watch for changes"
    )
):
    """Run a development server with hot reload and worker support"""
    async def run_app(kitchen_path: str, config_file: Optional[Path], watch_dirs: List[Path], reload: bool):
        # Load config
        config = WhiskConfig.from_file(config_file) if config_file else WhiskConfig()
        
        # Ensure NATS config exists
        if config.nats is None:
            config.nats = NatsConfig()
        
        # Import the kitchen module
        module_path, attr = kitchen_path.split(":")
        kitchen_module = importlib.import_module(module_path)
        kitchen = getattr(kitchen_module, attr)
        
        # Setup client
        client = WhiskClient(
            nats_url=config.nats.url,
            user=config.nats.user,
            password=config.nats.password,
            kitchen=kitchen
        )
        
        try:
            if reload:
                # Watch for file changes
                async for changes in awatch(*watch_dirs):
                    typer.echo(f"Detected changes: {changes}")
                    # Reload kitchen module
                    importlib.reload(kitchen_module)
                    kitchen = getattr(kitchen_module, attr)
            else:
                # Run the client app
                await client.app.run()
        except KeyboardInterrupt:
            typer.echo("Shutting down...")
    
    # Run with multiple workers if specified
    if workers > 1:
        import multiprocessing
        processes = []
        for _ in range(workers):
            p = multiprocessing.Process(
                target=asyncio.run, 
                args=(run_app(kitchen, config_file, watch_dirs, reload),)
            )
            p.start()
            processes.append(p)
        
        try:
            for p in processes:
                p.join()
        except KeyboardInterrupt:
            for p in processes:
                p.terminate()
    else:
        # Single worker mode
        try:
            asyncio.run(run_app(kitchen, config_file, watch_dirs, reload))
        except KeyboardInterrupt:
            typer.echo("Shutting down...")

def run(
    app: str = typer.Argument(..., help="App to run"),
    config: str = typer.Option(None, "--config", "-c", help="Config file"),
):
    """Run a Whisk application"""
    # ... implementation ... 