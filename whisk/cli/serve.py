import uvicorn
import logging
from ..config import WhiskConfig, ServerConfig
from ..router import WhiskRouter

logger = logging.getLogger(__name__)

def get_application():
    """Factory function for uvicorn"""
    from whisk.examples.app import kitchen
    
    # Initialize router with config
    config = WhiskConfig(server=ServerConfig(type="fastapi"))
    router = WhiskRouter(kitchen=kitchen, config=config)
    return router.router

def serve(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = True,
    workers: int = 1,
    log_level: str = "info",
):
    """Start the FastAPI server"""
    # Start server with factory
    uvicorn.run(
        "whisk.cli.serve:get_application",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        log_level=log_level,
        factory=True
    ) 