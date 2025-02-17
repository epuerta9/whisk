from pydantic import BaseModel, Field, PrivateAttr
from typing import List, Optional, Dict, Any
import time
from pydantic import ConfigDict


"""
Extra body for file requests using the OpenAI API
"""

class FileExtraBody(BaseModel):
    client_id: str
    namespace: str
    label: str
    version: str | None = None
    metadata: str | None = None

class ChatExtraBody(BaseModel):
    namespace: str | None = None
    version: str | None = None

class Message(BaseModel):
    role: str
    content: str
    name: Optional[str] = None

class ChatCompletionRequest(BaseModel):
    messages: List[Message]
    model: str = "default"
    stream: bool = False
    stream_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None

class ChatResponseMessage(BaseModel):
    role: str = "assistant"
    content: str

class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatResponseMessage
    finish_reason: Optional[str] = "stop"

class ChatCompletionResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: str = Field(default_factory=lambda: f"chatcmpl-{int(time.time())}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionChoice]
    usage: Optional[Dict[str, int]] = None
    metadata: Optional[Dict[str, Any]] = None

class StreamingChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{int(time.time())}")
    object: str = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[Dict[str, Any]]

class ChatCompletionChunkDelta(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None

class ChatCompletionChunkChoice(BaseModel):
    index: int
    delta: ChatCompletionChunkDelta
    finish_reason: Optional[str] = None

class ChatCompletionChunk(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[ChatCompletionChunkChoice]
