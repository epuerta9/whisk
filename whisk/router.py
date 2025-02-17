from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from faststream.nats.fastapi import NatsRouter
from typing import Optional
from .config import WhiskConfig
from .kitchenai_sdk.kitchenai import KitchenAIApp
from .kitchenai_sdk.http_schema import (
    ChatCompletionRequest,
    ChatCompletionResponse
)
import json
from .api.models import router as models_router
from .api.chat import router as chat_router
from .api.files import router as files_router
from .api.commands import CommandMiddleware

import logging

logger = logging.getLogger(__name__)

class WhiskRouter:
    """FastAPI router with command support"""
    def __init__(
        self,
        kitchen: KitchenAIApp,
        config: WhiskConfig,
        enable_commands: bool = False
    ):
        self.kitchen = kitchen
        self.config = config
        logger.info(f"Initializing FastAPIRouter with enable_commands={enable_commands}")
        
        self.router = FastAPI(
            title="Whisk API",
            description="KitchenAI API server",
            version="1.0.0",
            openapi_url="/openapi.json",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # Add CORS middleware
        self.router.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Disable command middleware for now
        self.command_middleware = None
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup all API routes"""
        prefix = self.config.server.fastapi.prefix
        
        # Mount API routers with prefix
        self.router.include_router(models_router, prefix=prefix)
        self.router.include_router(chat_router, prefix=prefix)
        self.router.include_router(files_router, prefix=prefix)
        
        # Add OPTIONS and GET handlers for models
        @self.router.options(f"{prefix}/models")
        async def models_options():
            return {}
        
        @self.router.get(f"{prefix}/models")
        async def list_models():
            """List available models"""
            # Get all registered chat handlers as models
            handlers = self.kitchen.chat.list_tasks()
            return {
                "object": "list",
                "data": [
                    {
                        "id": handler_name,
                        "object": "model",
                        "created": 1677610602,
                        "owned_by": "whisk"
                    }
                    for handler_name in handlers
                ]
            }
        
        @self.router.options(f"{prefix}/chat/completions")
        async def chat_options():
            return {}
        
        # Setup chat completions endpoint
        @self.router.post(f"{prefix}/chat/completions")
        async def chat_completions(request: Request):
            data = await request.json()
            chat_request = ChatCompletionRequest(**data)
            
            # Get the task for the requested model
            task = self.kitchen.chat.get_task(chat_request.model)
            logger.info(f"Looking for handler for model: {chat_request.model}")
            logger.info(f"Available handlers: {self.kitchen.chat.list_tasks()}")
            
            if not task:
                raise HTTPException(status_code=404, detail=f"Chat handler not found for model: {chat_request.model}")
            
            # Handle streaming
            if chat_request.stream:
                return StreamingResponse(
                    self._stream_response(task, chat_request),
                    media_type="text/event-stream"
                )
            
            # Normal response
            response = await task(chat_request)
            return response
    
    async def _stream_response(self, task, request: ChatCompletionRequest):
        """Helper method to handle streaming responses"""
        response = await task(request)
        
        # Format each chunk as SSE
        for choice in response.choices:
            chunk = {
                "id": response.id,
                "object": "chat.completion.chunk",
                "created": response.created,
                "model": response.model,
                "choices": [{
                    "index": choice.index,
                    "delta": {
                        "role": "assistant",
                        "content": choice.message.content
                    },
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
        
        # Send final chunk with finish_reason
        final_chunk = {
            "id": response.id,
            "object": "chat.completion.chunk",
            "created": response.created,
            "model": response.model,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"
    
    def mount(self):
        """Mount all routes and start services"""
        # NATS router is mounted last if it exists
        if hasattr(self, 'nats_router'):
            self.router.include_router(self.nats_router) 