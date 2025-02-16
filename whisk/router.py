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
        self.app = fastapi_app or FastAPI()
        
        # Initialize NATS router if needed
        if config.server.type in ["nats", "both"]:
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
            task = self.kitchen.query.get_task("chat")
            if not task:
                raise HTTPException(404, "Chat handler not found")
            
            query = WhiskQuerySchema(
                query=request.messages[-1].content,
                stream=request.stream,
                metadata={"model": request.model},
                messages=request.messages,
                label="chat"
            )
            
            if request.stream:
                return StreamingResponse(
                    self._stream_response(task, query),
                    media_type="text/event-stream"
                )
            
            response = await task(query)
            return ChatCompletionResponse(
                model=request.model,
                choices=[
                    ChatCompletionChoice(
                        message=ChatResponseMessage(
                            content=response["output"]
                        )
                    )
                ]
            )
    
    async def _stream_response(self, task, query):
        """Helper method to handle streaming responses"""
        response = await task(query)
        print(f"DEBUG: Response from task: {response}")  # Debug line
        
        if "stream_gen" not in response:
            # Format non-streaming response as SSE
            yield f"data: {json.dumps(response)}\n\n"
            return

        # Ensure we have a generator
        stream_gen = response["stream_gen"]
        if not callable(stream_gen):
            print(f"DEBUG: stream_gen is not callable: {stream_gen}")
            return
            
        try:
            async for chunk in stream_gen():
                # Format each chunk as a StreamingChatCompletionResponse
                stream_response = StreamingChatCompletionResponse(
                    model=query.metadata.get("model", "unknown"),
                    choices=[{
                        "delta": {"content": chunk["output"]},
                        "index": 0,
                        "finish_reason": None
                    }]
                )
                # Use model_dump instead of dict (Pydantic v2 recommendation)
                response_str = f"data: {json.dumps(stream_response.model_dump())}\n\n"
                print(f"DEBUG: Yielding chunk: {response_str}")  # Debug line
                yield response_str
            
            # Send final [DONE] message
            yield "data: [DONE]\n\n"
        except Exception as e:
            print(f"DEBUG: Error in streaming: {e}")
            raise
    
    def mount(self):
        """Mount all routes and start services"""
        if hasattr(self, 'nats_router'):
            self.app.include_router(self.nats_router) 