from typing import Dict, Any, Callable, Union, AsyncGenerator
from functools import wraps
from ..base import TaskRegistry
from ..schema import ChatInput, ChatResponse, DependencyType
from ..http_schema import ChatCompletionResponse, ChatResponseMessage, ChatCompletionChoice
import asyncio
import time

class ChatTask(TaskRegistry):
    """Chat task registry"""
    
    def __init__(self, namespace: str, manager=None):
        super().__init__(namespace, manager)
        self.task_type = "chat"

    def handler(self, name: str, *dependencies: Union[DependencyType, str]):
        """Decorator for simplified chat handlers"""
        def decorator(func: Callable[[ChatInput], Union[ChatResponse, AsyncGenerator]]):
            @wraps(func)
            async def wrapper(request: Any):
                # Inject dependencies
                kwargs = {}
                if self._manager:
                    for dep in dependencies:
                        dep_key = dep.value if hasattr(dep, 'value') else dep
                        if self._manager.has_dependency(dep):
                            kwargs[dep_key] = self._manager.get_dependency(dep)
                        else:
                            raise KeyError(f"Required dependency {dep} not found")

                # Convert request to ChatInput
                chat_input = ChatInput.from_request(request)
                
                # Call handler - don't await yet
                response = func(chat_input, **kwargs)
                
                # Handle streaming responses
                if request.stream:
                    # For streaming, we want the async generator
                    if hasattr(response, '__aiter__'):
                        # Return async generator for streaming
                        async def stream_generator():
                            chunk_id = f"chatcmpl-{int(time.time())}"
                            async for chunk in response:
                                if isinstance(chunk, ChatResponse):
                                    yield chunk.to_openai_chunk(chunk_id, model=request.model)
                                else:
                                    yield ChatResponse(content=str(chunk)).to_openai_chunk(chunk_id, model=request.model)
                            # Send final chunk
                            yield {
                                "id": chunk_id,
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": request.model,
                                "choices": [{
                                    "index": 0,
                                    "delta": {},
                                    "finish_reason": "stop"
                                }]
                            }
                        return stream_generator()
                    else:
                        # If it's a coroutine, await it and wrap in generator
                        response = await response
                        async def single_chunk_generator():
                            chunk_id = f"chatcmpl-{int(time.time())}"
                            if isinstance(response, ChatResponse):
                                yield response.to_openai_chunk(chunk_id, model=request.model)
                            else:
                                yield ChatResponse(content=str(response)).to_openai_chunk(chunk_id, model=request.model)
                            # Send final chunk
                            yield {
                                "id": chunk_id,
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": request.model,
                                "choices": [{
                                    "index": 0,
                                    "delta": {},
                                    "finish_reason": "stop"
                                }]
                            }
                        return single_chunk_generator()
                
                # For non-streaming, await if it's a coroutine
                if asyncio.iscoroutine(response):
                    response = await response
                
                # Handle non-streaming responses
                if isinstance(response, ChatCompletionResponse):
                    # Already in correct format
                    return response
                elif isinstance(response, ChatResponse):
                    # Convert ChatResponse to ChatCompletionResponse
                    return ChatCompletionResponse(
                        model=request.model,
                        choices=[
                            ChatCompletionChoice(
                                index=0,
                                message=ChatResponseMessage(
                                    role=response.role,
                                    content=response.content,
                                    name=response.name
                                ),
                                finish_reason="stop"
                            )
                        ],
                        metadata={"sources": [s.model_dump() for s in response.sources]} if response.sources else None
                    )
                elif isinstance(response, dict):
                    # If it's a simple dict with just content, convert to proper format
                    if "response" in response:
                        return ChatCompletionResponse(
                            model=request.model,
                            choices=[
                                ChatCompletionChoice(
                                    index=0,
                                    message=ChatResponseMessage(
                                        role="assistant",
                                        content=response["response"]
                                    ),
                                    finish_reason="stop"
                                )
                            ]
                        )
                    # Otherwise try to convert dict to ChatCompletionResponse directly
                    return ChatCompletionResponse(**response)
                else:
                    # Convert any other response to ChatCompletionResponse
                    return ChatCompletionResponse(
                        model=request.model,
                        choices=[
                            ChatCompletionChoice(
                                index=0,
                                message=ChatResponseMessage(
                                    role="assistant",
                                    content=str(response)
                                ),
                                finish_reason="stop"
                            )
                        ]
                    )
                
            return self.register_task(name, wrapper)
        return decorator

    def get_task(self, name: str) -> Callable:
        """Get a chat task by name"""
        return self._tasks.get(name)

    def list_tasks(self) -> Dict[str, Callable]:
        """List all registered chat tasks"""
        return self._tasks 