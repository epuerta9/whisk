from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any, AsyncGenerator
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

router = APIRouter(
    prefix="/v1",
    tags=["Chat"]
)

def get_kitchen_app() -> KitchenAIApp:
    """Dependency to get the KitchenAI app instance"""
    from whisk.examples.app import kitchen
    return kitchen

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

async def stream_response(task, request: ChatCompletionRequest):
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

@router.post("/chat/completions", response_model=None)
async def chat_completions(
    request: ChatCompletionRequest,
    kitchen: KitchenAIApp = Depends(get_kitchen_app)
):
    """Create a chat completion"""
    task = kitchen.chat.get_task("chat.completions")
    if not task:
        raise HTTPException(status_code=404, detail="Chat handler not found")
    
    if request.stream:
        return StreamingResponse(
            stream_response(task, request),
            media_type="text/event-stream"
        )
    
    response = await task(request)
    return response 