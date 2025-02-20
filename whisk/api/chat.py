from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any, AsyncGenerator, Callable
import json
import time
import asyncio
from ..kitchenai_sdk.schema import WhiskQuerySchema
from ..kitchenai_sdk.http_schema import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatResponseMessage,
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
    ChatCompletionChunkDelta
)
from ..kitchenai_sdk.kitchenai import KitchenAIApp
from ..dependencies import get_kitchen_app

router = APIRouter(
    prefix="/v1",
    tags=["Chat"]
)

def get_chat_task(request: ChatCompletionRequest) -> Callable:
    """Get the appropriate chat task based on the request"""
    kitchen = get_kitchen_app()
    
    # Extract handler name from model field
    handler = request.model.split("/")[-1]
    
    # Get the task
    task = kitchen.chat.get_task(handler)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Chat handler '{handler}' not found"
        )
    
    return task

def parse_system_metadata(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Extract metadata from system messages"""
    metadata = {}
    
    for msg in messages:
        if msg["role"] == "system":
            content = msg["content"]
            
            # Try to parse as JSON if content starts with METADATA:
            if content.startswith("METADATA:"):
                try:
                    json_str = content.replace("METADATA:", "").strip()
                    metadata.update(json.loads(json_str))
                    continue
                except json.JSONDecodeError:
                    pass
            
            # Try to parse as key-value pairs
            if "#METADATA" in content:
                metadata_section = content.split("#METADATA")[1].strip()
                for line in metadata_section.split("\n"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        metadata[key.strip()] = value.strip()
                continue
    
    return metadata

async def stream_response(task: Callable, request: ChatCompletionRequest):
    """Stream chat completion response"""
    response = task(request)  # Don't await yet
    
    # If it's a coroutine (non-streaming response), await it
    if asyncio.iscoroutine(response):
        response = await response
        
    # If it's an async generator, stream it
    if hasattr(response, '__aiter__'):
        try:
            async for chunk in response:
                # If chunk is already formatted as OpenAI chunk, send it directly
                if isinstance(chunk, dict) and "choices" in chunk:
                    yield f"data: {json.dumps(chunk)}\n\n"
                # Otherwise format it as a chunk
                else:
                    response_chunk = {
                        "id": f"chatcmpl-{int(time.time())}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": request.model,
                        "choices": [{
                            "index": 0,
                            "delta": {
                                "role": "assistant",
                                "content": chunk.content if hasattr(chunk, 'content') else str(chunk)
                            },
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(response_chunk)}\n\n"
            
            yield "data: [DONE]\n\n"
        except Exception as e:
            print(f"Streaming error: {str(e)}")
            raise
    else:
        raise ValueError("Expected streaming response but got non-streaming response")

@router.post(
    "/chat/completions",
    response_model=ChatCompletionResponse,
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "model": ChatCompletionResponse
                },
                "text/event-stream": {
                    "description": "Stream of server-sent events"
                }
            }
        }
    }
)
async def chat_completions(request: ChatCompletionRequest) -> Union[ChatCompletionResponse, StreamingResponse]:
    """Chat completion endpoint"""
    task = get_chat_task(request)
    
    if request.stream:
        return StreamingResponse(
            stream_response(task, request),
            media_type="text/event-stream"
        )
    
    response = await task(request)
    # Convert dict response to ChatCompletionResponse if needed
    if isinstance(response, dict):
        response = ChatCompletionResponse(**response)
    # Return the raw dict for proper JSON serialization
    return response.model_dump(mode='json') 