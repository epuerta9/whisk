from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from faststream.nats.fastapi import NatsRouter
from typing import Optional
from .config import WhiskConfig
from .kitchenai_sdk.kitchenai import KitchenAIApp
from .kitchenai_sdk.schema import WhiskQuerySchema
from .kitchenai_sdk.http_schema import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatResponseMessage,
    StreamingChatCompletionResponse
)
import json

class WhiskRouter:
    def __init__(
        self,
        kitchen: KitchenAIApp,
        config: WhiskConfig,
        fastapi_app: Optional[FastAPI] = None
    ):
        self.kitchen = kitchen
        self.config = config
        self.app = fastapi_app
        
        # Initialize NATS router only if explicitly configured
        if (config.server.type in ["nats", "both"] and 
            config.server.nats is not None and 
            config.client and config.client.id):
            self.nats_router = NatsRouter(
                config.nats.url,
                user=config.nats.user,
                password=config.nats.password,
                name=config.client.id
            )
            self._setup_nats_handlers()
            
        # Initialize FastAPI routes if needed
        if config.server.type in ["fastapi", "both"] and self.app:
            self._setup_fastapi_routes()
    
    def _setup_nats_handlers(self):
        """Setup NATS message handlers"""
        @self.nats_router.subscriber(
            f"kitchenai.service.{self.config.client.id}.query.*",
            include_in_schema=True,
            description="Handle query requests"
        )
        async def handle_query(msg: WhiskQuerySchema) -> dict:
            task = self.kitchen.query.get_task(msg.label)
            if task:
                return await task(msg)
            return {"error": f"No task found for label {msg.label}"}
            
        # Add other NATS handlers as needed...
    
    def _setup_fastapi_routes(self):
        """Setup FastAPI routes including OpenAI-compatible endpoints"""
        @self.app.post(f"{self.config.server.fastapi.prefix}/chat/completions")
        async def chat_completions(request: ChatCompletionRequest):
            task = self.kitchen.chat.get_task("chat.completions")
            if not task:
                raise HTTPException(status_code=404, detail="Chat handler not found")
            
            if request.stream:
                return StreamingResponse(
                    self._stream_response(task, request),
                    media_type="text/event-stream"
                )
            
            response = await task(request)
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
                    "index": choice["index"],
                    "delta": {
                        "role": "assistant",
                        "content": choice["message"]["content"]
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
        if hasattr(self, 'nats_router'):
            self.app.include_router(self.nats_router) 