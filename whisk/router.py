from fastapi import FastAPI, HTTPException, Request, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Callable
from .config import WhiskConfig
from .kitchenai_sdk.kitchenai import KitchenAIApp
from .api import chat_router, files_router, models_router

import logging
logger = logging.getLogger(__name__)

# Global kitchen app instance for dependency injection
_current_kitchen_app = None

def get_kitchen_app() -> KitchenAIApp:
    """Dependency to get KitchenAI app instance"""
    return _current_kitchen_app

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
        self._fastapi_app = fastapi_app
        self.before_setup = before_setup
        self.after_setup = after_setup

        # Store kitchen app for dependency injection
        global _current_kitchen_app
        _current_kitchen_app = kitchen_app

    @property
    def app(self) -> FastAPI:
        """Get or create the FastAPI app"""
        if self._fastapi_app is None:
            self._fastapi_app = self._create_fastapi_app()
        return self._fastapi_app

    def _create_fastapi_app(self) -> FastAPI:
        """Create and configure the FastAPI app"""
        # Create base FastAPI app
        fastapi_app = FastAPI(
            title="Whisk API",
            description="API for Whisk AI services",
            version="1.0.0",
            # Move docs to root
            docs_url="/docs",
            redoc_url="/redoc",
            openapi_url="/openapi.json"
        )

        # Run pre-setup callback
        if self.before_setup:
            self.before_setup(fastapi_app)

        # Add CORS middleware
        fastapi_app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Add kitchen app dependency and include routers
        for router in [chat_router, files_router, models_router]:
            router.dependencies = [Depends(get_kitchen_app)]
            fastapi_app.include_router(router)  # Routers already have /v1 prefix

        # Run post-setup callback
        if self.after_setup:
            self.after_setup(fastapi_app)

        return fastapi_app

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