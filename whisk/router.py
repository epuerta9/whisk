from fastapi import FastAPI, HTTPException, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Callable
from .config import WhiskConfig
from .kitchenai_sdk.kitchenai import KitchenAIApp
from .dependencies import set_kitchen_app

import logging
logger = logging.getLogger(__name__)

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
        """Run the FastAPI server"""
        import uvicorn
        
        host = host or self.config.server.fastapi.host
        port = port or self.config.server.fastapi.port
        
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level="info"
        ) 