from pydantic import BaseModel, ConfigDict, computed_field, Field, PrivateAttr
from typing import List, Optional, Dict, Any, Callable, Union, AsyncGenerator
from enum import StrEnum, auto
import time
from .http_schema import Message
import asyncio


class TokenCountSchema(BaseModel):
    embedding_tokens: Optional[int] = None
    llm_prompt_tokens: Optional[int] = None 
    llm_completion_tokens: Optional[int] = None
    total_llm_tokens: Optional[int] = None


class SourceNodeSchema(BaseModel):
    text: str
    metadata: Dict[str, Any]
    score: float


# Keep existing schemas for backward compatibility
class WhiskQuerySchema(BaseModel):
    query: str
    stream: bool = False
    stream_id: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None
    label: Optional[str] = None
    messages: Optional[List[object]] = None

# New OpenAI-compatible schemas
class ChatMessage(BaseModel):
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

class ChatCompletionResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: str = Field(default_factory=lambda: f"chatcmpl-{int(time.time())}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[Dict[str, Any]]  # Standard OpenAI format
    usage: Optional[Dict[str, int]] = None
    system_fingerprint: Optional[str] = None
    
    # Internal fields for RAG/Agent context
    _retrieval_context: Optional[List[SourceNodeSchema]] = PrivateAttr(default=None)
    
    def add_rag_context(self, context: List[SourceNodeSchema]):
        """Add RAG context to the response"""
        self._retrieval_context = context
        # Add context to the message content in a structured way
        if self.choices and len(self.choices) > 0:
            message = self.choices[0]["message"]
            content = message["content"]
            context_str = "\n\nSources:\n" + "\n".join(
                f"- {node.text} (score: {node.score})"
                for node in context
            )
            message["content"] = content + context_str

    @classmethod
    def from_rag_response(cls, request: ChatCompletionRequest, response, context: List[SourceNodeSchema]):
        """Create a chat completion response from a RAG response"""
        instance = cls(
            model=request.model,
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response.response
                },
                "finish_reason": "stop"
            }]
        )
        instance.add_rag_context(context)
        return instance


class WhiskQueryBaseResponseSchema(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    input: Optional[str] = None
    output: Optional[str] = None
    retrieval_context: Optional[List[SourceNodeSchema]] = None
    stream_gen: Any | None = None
    metadata: Optional[Dict[str, Any]] = {}
    token_counts: Optional[TokenCountSchema] = None


    # OpenAI Chat Completion Schema as optional for more context. Will come is as a dict.
    messages: Optional[List[object]] = None
    
    @classmethod
    def from_llama_response(cls, data, response, metadata=None, token_counts: TokenCountSchema | None = None):
        source_nodes = []
        if hasattr(response, 'source_nodes'):
            for node in response.source_nodes:
                source_nodes.append(SourceNodeSchema(
                    text=node.node.text,
                    metadata=node.node.metadata,
                    score=node.score
                ))
        if metadata and response.metadata:
            response.metadata.update(metadata)
        return cls(
            input=data.query,
            output=response.response,
            retrieval_context=source_nodes,
            metadata=response.metadata,
            token_counts=token_counts
        )
    
    @classmethod
    def from_llama_response_stream(cls, data, response, stream_gen, metadata: dict[str, Any] | None = {}, token_counts: TokenCountSchema | None = None):
        source_nodes = []
        if hasattr(response, 'source_nodes'):
            for node in response.source_nodes:
                source_nodes.append(SourceNodeSchema(
                    text=node.node.text,
                    metadata=node.node.metadata,
                    score=node.score
                ))

        if metadata:
            response.metadata.update(metadata)
        return cls(
            input=data.query,
            retrieval_context=source_nodes,
            metadata=response.metadata,
            stream_gen=stream_gen,
            token_counts=token_counts
        )
    
    @classmethod
    def with_string_retrieval_context(cls, data, response: str, retrieval_context: List[str], metadata: dict[str, Any] | None = {}, token_counts: TokenCountSchema | None = None):
        return cls(
            input=data.query,
            output=response.response,
            retrieval_context=[SourceNodeSchema(text=context, metadata=metadata, score=1.0) for context in retrieval_context],
            metadata=response.metadata,
            token_counts=token_counts
        )
    
    @classmethod
    def from_llm_invoke(cls, input: str, output: str, metadata=None, token_counts: TokenCountSchema | None = None):        
        return cls(
            input=input,
            output=output,
            metadata=metadata,
            token_counts=token_counts
        )

class WhiskStorageStatus(StrEnum):
    PENDING = "pending"
    ERROR = "error"
    COMPLETE = "complete"
    ACK = "ack"

class WhiskStorageSchema(BaseModel):
    id: int
    name: str
    label: str 
    data: Optional[bytes] = bytes()
    metadata: Optional[Dict[str, str]] = None
    extension: Optional[str] = None

class WhiskStorageGetRequestSchema(BaseModel):
    id: int
    presigned: bool = False


class WhiskStorageGetResponseSchema(BaseModel):
    presigned_url: Optional[str] = None
    error: Optional[str] = None

class WhiskStorageResponseSchema(BaseModel):
    id: int
    name: str
    label: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    files: Optional[List[Any]] = None
    deleted: Optional[bool] = None
    created_at: Optional[int] = None
    status: Optional[str] = None

    @classmethod
    def with_token_counts(cls, token_counts: TokenCountSchema):
        return cls(token_counts=token_counts)

class WhiskAgentResponseSchema(BaseModel):  
    response: str

class WhiskEmbedSchema(BaseModel):
    label: str
    text: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None

class WhiskEmbedResponseSchema(BaseModel):
    metadata: Optional[Dict[str, Any]] = None
    token_counts: Optional[TokenCountSchema] = None

    @classmethod
    def with_token_counts(cls, token_counts: TokenCountSchema):
        return cls(token_counts=token_counts)

class WhiskBroadcastSchema(BaseModel):
    """Schema for broadcast messages"""
    message: str
    type: str = "info"  # info, warning, error, etc.
    metadata: Optional[Dict[str, Any]] = None

class WhiskBroadcastResponseSchema(BaseModel):
    """Schema for broadcast responses"""
    message: str
    type: str
    metadata: Optional[Dict[str, Any]] = None
    token_counts: Optional[TokenCountSchema] = None

    @classmethod
    def from_broadcast(cls, broadcast: WhiskBroadcastSchema, token_counts: TokenCountSchema | None = None):
        return cls(
            message=broadcast.message,
            type=broadcast.type,
            metadata=broadcast.metadata,
            token_counts=token_counts
        )


class NatsMessageMetadata(BaseModel):
    content_type: str
    correlation_id: str
    reply_to: Optional[str] = None
    message_id: str

class NatsMessage(BaseModel):
    """
    Used for Request/Response messages
    """
    body: bytes
    headers: Dict[str, str]
    metadata: NatsMessageMetadata
    decoded_body: Dict[str, Any]

    @classmethod
    def from_faststream(cls, msg):
        return cls(
            body=msg.body,
            headers=msg.headers,
            metadata=NatsMessageMetadata(
                content_type=msg.content_type,
                correlation_id=msg.correlation_id,
                reply_to=msg.reply_to,
                message_id=msg.message_id,
                request_id=msg._decoded_body.get('request_id'),
            subject=msg.raw_message.subject,
            client_id=msg._decoded_body.get('client_id')
            ),
            decoded_body=msg._decoded_body
        )

class DependencyType(str, auto):
    """Types of dependencies that can be registered"""
    LLM = "llm"
    VECTOR_STORE = "vector_store"
    SYSTEM_PROMPT = "system_prompt"
    EMBEDDINGS = "embeddings"
    RETRIEVER = "retriever"

# Input types
class Message(BaseModel):
    """A single chat message"""
    role: str
    content: str
    name: Optional[str] = None

class ChatInput(BaseModel):
    """Simplified chat input"""
    messages: List[Message]
    model: str = "default"
    stream: bool = False
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_request(cls, request: Any) -> "ChatInput":
        """Create from OpenAI request"""
        messages = []
        for msg in request.messages:
            if isinstance(msg, dict):
                messages.append(Message(**msg))
            elif isinstance(msg, Message):
                messages.append(msg)
            elif hasattr(msg, 'role') and hasattr(msg, 'content'):
                # Handle http_schema.Message and other message-like objects
                messages.append(Message(
                    role=msg.role,
                    content=msg.content,
                    name=getattr(msg, 'name', None)
                ))
            else:
                raise ValueError(f"Invalid message type: {type(msg)}")
                
        return cls(
            messages=messages,
            model=request.model,
            stream=request.stream,
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens,
            metadata=request.metadata
        )

# Output types
class SourceNode(BaseModel):
    """Source document with metadata"""
    text: str
    metadata: Dict[str, Any]
    score: Optional[float] = None

class ChatResponse(BaseModel):
    """Simplified chat response"""
    content: str
    role: str = "assistant"
    name: Optional[str] = None
    sources: Optional[List[SourceNode]] = None  # Added for RAG responses

    def to_openai_response(self, model: str = "default") -> Dict[str, Any]:
        """Convert to OpenAI format"""
        response = {
            "id": f"chat-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": self.role,
                    "content": self.content,
                    **({"name": self.name} if self.name else {})
                },
                "finish_reason": "stop"
            }]
        }
        
        # Include sources in response metadata if available
        if self.sources:
            response["metadata"] = {
                "sources": [source.dict() for source in self.sources]
            }
        
        return response

    @classmethod
    async def stream(cls, content_stream, **kwargs) -> AsyncGenerator["ChatResponse", None]:
        """Create a streaming response"""
        async for chunk in content_stream:
            # Handle different types of chunks
            if isinstance(chunk, str):
                content = chunk
            elif hasattr(chunk, 'content'):
                content = chunk.content
            else:
                content = str(chunk)
                
            yield cls(
                content=content,
                role=kwargs.get('role', 'assistant'),
                name=kwargs.get('name'),
                sources=kwargs.get('sources')
            )

    def to_openai_chunk(self, chunk_id: str, model: str = None) -> Dict:
        """Convert to OpenAI chat completion chunk format"""
        return {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,  # Include model in the response
            "choices": [{
                "index": 0,
                "delta": {
                    "role": self.role,
                    "content": self.content
                },
                "finish_reason": None
            }]
        }

class StorageRequest(BaseModel):
    """Storage task request"""
    action: str  # upload, get, delete, list
    file_id: Optional[str] = None
    content: Optional[bytes] = None
    filename: Optional[str] = None
    purpose: Optional[str] = None
    model: Optional[str] = None  # Add model field for handler routing
    metadata: Optional[Dict[str, Any]] = None

class StorageResponse(BaseModel):
    """Storage task response"""
    file_id: str
    filename: str
    content: Optional[bytes] = None
    created_at: int = Field(default_factory=lambda: int(time.time()))
    metadata: Optional[Dict[str, Any]] = None
    deleted: Optional[bool] = None