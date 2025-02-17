from pydantic import BaseModel, Field, PrivateAttr
from typing import List, Optional, Dict, Any, Union
import time
from pydantic import ConfigDict
from pydantic import field_validator


"""
Extra body for file requests using the OpenAI API
"""

class FileExtraBody(BaseModel):
    """
    Extra body for file requests.
    model: Format can be either:
        - "@namespace-version/label" (e.g. "@whisk-v1/my-handler")
        - "label" (e.g. "my-handler")
    metadata: Optional metadata as string ("key1=value1,key2=value2") or dict
    """
    model: str = Field(..., description="Model identifier in format '@namespace-version/label' or 'label'")
    metadata: Optional[Union[str, Dict[str, Any]]] = Field(default=None, description="Additional metadata")

    @field_validator('metadata')
    def validate_metadata(cls, v):
        if isinstance(v, str):
            # Convert string format to dict
            try:
                return dict(item.split("=") for item in v.split(","))
            except Exception as e:
                raise ValueError(f"Invalid metadata string format. Expected 'key1=value1,key2=value2', got {v}")
        return v

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

class FileResponse(BaseModel):
    """OpenAI-compatible file response"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: str = Field(..., description="The file identifier.")
    object: str = Field("file", description="Always 'file'.")
    bytes: int = Field(..., description="The size of the file in bytes.")
    created_at: int = Field(..., description="Unix timestamp (in seconds) of when the file was created.")
    filename: str = Field(..., description="The name of the file.")
    purpose: str = Field(..., description="Intended purpose of the file.")
    status: Optional[str] = Field(None, description="Status of the file.")
    status_details: Optional[str] = Field(None, description="Additional status details.")

class FileListResponse(BaseModel):
    """
    OpenAI-compatible file list response with pagination support.
    Matches the format expected by SyncCursorPage[FileObject].
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    object: str = Field("list", description="Always 'list' for a list of files.")
    data: List[FileResponse]
    has_more: bool = Field(False, description="Whether there are more files to fetch")
    first_id: Optional[str] = Field(None, description="ID of the first file in the list")
    last_id: Optional[str] = Field(None, description="ID of the last file in the list")
    after: Optional[str] = Field(None, description="Cursor for fetching next page")
    before: Optional[str] = Field(None, description="Cursor for fetching previous page")

class FileDeleteResponse(BaseModel):
    """OpenAI-compatible file deletion response"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: str = Field(..., description="The file identifier.")
    object: str = Field("file", description="Always 'file'.")
    deleted: bool = Field(..., description="Indicates if the file was deleted successfully.")

class ModelResponse(BaseModel):
    """Response model for a single model"""
    id: str
    object: str = "model"
    created: int
    owned_by: str
    permissions: Optional[List[str]] = None
    root: Optional[str] = None
    parent: Optional[str] = None

class ModelListResponse(BaseModel):
    """Response model for listing models"""
    object: str = "list"
    data: List[ModelResponse]
    has_more: bool = False
