import asyncio
import nest_asyncio
import uvicorn

from fastapi import FastAPI, HTTPException, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Callable
from .config import WhiskConfig
from .kitchenai_sdk.kitchenai import KitchenAIApp
from .dependencies import set_kitchen_app

import logging
logger = logging.getLogger(__name__)

# Globals to hold the server instance and task for notebook usage
_global_server = None
_global_server_task = None

class WhiskRouter:
    """Router for Whisk API endpoints"""
    def __init__(
        self, 
        kitchen_app: KitchenAIApp, 
        config: WhiskConfig,
        fastapi_app: Optional[FastAPI] = None,
        before_setup: Optional[Callable[[FastAPI], None]] = None,
        after_setup: Optional[Callable[[FastAPI], None]] = None
    ):
        """
        Initialize WhiskRouter
        
        Args:
            kitchen_app: KitchenAI application instance
            config: WhiskConfig instance
            fastapi_app: Optional FastAPI app to use instead of creating new one
            before_setup: Optional callback to run before setting up routes
            after_setup: Optional callback to run after setting up routes
        """
        self.kitchen_app = kitchen_app
        self.config = config
        self.app = fastapi_app or FastAPI()
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allows all origins
            allow_credentials=True,
            allow_methods=["*"],  # Allows all methods
            allow_headers=["*"],  # Allows all headers
        )
        
        # Set up the kitchen app in the dependency system
        set_kitchen_app(kitchen_app)
        
        # Run before setup hook
        if before_setup:
            before_setup(self.app)
        
        # Get and include routers
        from .api import get_routers
        for router in get_routers():
            self.app.include_router(router)
        
        # Run after setup hook
        if after_setup:
            after_setup(self.app)

    def run(self, host: Optional[str] = None, port: Optional[int] = None):
        """Run the FastAPI server (blocking version)"""
        host = host or self.config.server.fastapi.host
        port = port or self.config.server.fastapi.port
        
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level="info"
        )
    
    def run_in_notebook(self, host: Optional[str] = None, port: Optional[int] = None):
        """
        Run the FastAPI server in a Jupyter notebook non-blocking way.
        This method uses nest_asyncio to run the server in the background and
        global variables to manage the server instance so you can safely restart it.
        """
        global _global_server, _global_server_task

        # Allow nested event loops inside the notebook
        nest_asyncio.apply()

        host = host or self.config.server.fastapi.host
        port = port or self.config.server.fastapi.port

        # Stop an existing server if it is running
        self.stop_in_notebook()

        # Create a new Uvicorn server configuration for our app
        config = uvicorn.Config(self.app, host=host, port=port, log_level="info")
        _global_server = uvicorn.Server(config)

        loop = asyncio.get_event_loop()

        async def serve():
            await _global_server.serve()

        _global_server_task = loop.create_task(serve())
        print(f"Whisk server started on http://{host}:{port} (in background)")

    def stop_in_notebook(self):
        """
        Gracefully shut down the FastAPI server if it's running in the notebook.
        """
        global _global_server, _global_server_task

        if _global_server is not None and not _global_server.should_exit:
            print("Shutting down existing Whisk server...")
            _global_server.should_exit = True

        if _global_server_task is not None and not _global_server_task.done():
            loop = asyncio.get_event_loop()
            # Wait until the server task completes shutting down
            loop.run_until_complete(_global_server_task)

        _global_server = None
        _global_server_task = None
        print("Whisk server stopped.")
