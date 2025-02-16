from fastapi import APIRouter, HTTPException
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

router = APIRouter(prefix="/v1")

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

async def stream_response(content: str) -> AsyncGenerator[str, None]:
    """Stream response in OpenAI-compatible format"""
    # Split content into words for demonstration
    words = content.split()
    
    for i, word in enumerate(words):
        chunk = ChatCompletionChunk(
            id=f"chat-{time.time()}",
            object="chat.completion.chunk",
            created=int(time.time()),
            model="whisk-default",
            choices=[
                ChatCompletionChunkChoice(
                    index=0,
                    delta=ChatCompletionChunkDelta(
                        role="assistant" if i == 0 else None,
                        content=word + " "
                    ),
                    finish_reason=None if i < len(words) - 1 else "stop"
                )
            ]
        )
        yield f"data: {chunk.json()}\n\n"
        await asyncio.sleep(0.1)  # Simulate delay
    
    yield "data: [DONE]\n\n"

@router.post("/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest) -> Union[ChatCompletionResponse, StreamingResponse]:
    """OpenAI-compatible chat completions endpoint"""
    
    # Extract metadata from system messages
    metadata = parse_system_metadata(request.messages)
    
    # Convert to WhiskQuerySchema
    query = WhiskQuerySchema(
        input=request.messages[-1]["content"],  # Last user message
        metadata=metadata,
        stream=request.stream
    )
    
    # Process query through kitchen
    # ... implementation here ...
    response_content = "This is a test response"  # Replace with actual response
    
    # Return streaming response if requested
    if request.stream:
        return StreamingResponse(
            stream_response(response_content),
            media_type="text/event-stream"
        )
    
    # Return normal response
    return ChatCompletionResponse(
        id=f"chat-{time.time()}",
        object="chat.completion",
        created=int(time.time()),
        model=request.model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatResponseMessage(
                    role="assistant",
                    content=response_content
                ),
                finish_reason="stop"
            )
        ]
    ) 