import pytest
from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.schema import (
    ChatInput,
    ChatResponse,
    SourceNode,
)
from whisk.kitchenai_sdk.http_schema import (  # Import HTTP models from http_schema
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatResponseMessage,
    Message  # Add this import
)
from whisk.kitchenai_sdk.schema import DependencyType

@pytest.fixture
def kitchen():
    return KitchenAIApp(namespace="test")

async def test_basic_chat_handler(kitchen):
    """Test basic chat completion handler"""
    
    @kitchen.chat.handler("chat.completions")
    async def handle_chat(request: ChatCompletionRequest):
        return ChatCompletionResponse(
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatResponseMessage(
                        role="assistant",
                        content="Test response"
                    ),
                    finish_reason="stop"
                )
            ]
        )

    request = ChatCompletionRequest(
        messages=[
            Message(role="user", content="Hello")  # Use Message instead of ChatMessage
        ],
        model="test-model"
    )
    
    handler = kitchen.chat.get_task("chat.completions")
    response = await handler(request)
    
    assert response.choices[0].message.content == "Test response"
    assert response.model == "test-model"

@pytest.mark.asyncio
async def test_chat_handler_with_llm(kitchen):
    """Test chat handler with LLM dependency"""

    class MockLLM:
        async def complete(self, messages):
            return "LLM response"

    llm = MockLLM()
    kitchen.register_dependency(DependencyType.LLM, llm)

    @kitchen.chat.handler("chat.completions", DependencyType.LLM)
    async def handle_chat(chat: ChatInput, llm: MockLLM) -> ChatResponse:
        response = await llm.complete(chat.messages)
        return ChatResponse(content=response)

    request = ChatCompletionRequest(
        messages=[Message(role="user", content="Hello")],
        model="test-model"
    )

    handler = kitchen.chat.get_task("chat.completions")
    response = await handler(request)
    assert response.choices[0].message.content == "LLM response"

async def test_chat_handler_with_token_counts(kitchen):
    """Test chat handler with token counting"""
    
    @kitchen.chat.handler("chat.completions")
    async def handle_chat(request: ChatCompletionRequest):
        return ChatCompletionResponse(
            model=request.model,
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Test response"
                },
                "finish_reason": "stop"
            }],
            usage={
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        )

    request = ChatCompletionRequest(
        messages=[
            Message(role="user", content="Hello")
        ]
    )
    
    handler = kitchen.chat.get_task("chat.completions")
    response = await handler(request)
    
    assert response.usage["prompt_tokens"] == 10
    assert response.usage["completion_tokens"] == 5
    assert response.usage["total_tokens"] == 15

@pytest.mark.asyncio
async def test_chat_handler_with_rag(kitchen):
    """Test RAG-enabled chat handler with sources"""
    
    # Mock vector store and LLM
    class MockVectorStore:
        def as_retriever(self, similarity_top_k=2):
            return self
            
        def retrieve(self, query):
            return [
                type('Node', (), {
                    'node': type('Doc', (), {
                        'text': "Paris is the capital of France",
                        'metadata': {'source': 'wiki.txt'}
                    }),
                    'score': 0.95
                })(),
                type('Node', (), {
                    'node': type('Doc', (), {
                        'text': "The Eiffel Tower is in Paris",
                        'metadata': {'source': 'landmarks.txt'}
                    }),
                    'score': 0.85
                })()
            ]

    class MockLLM:
        async def acomplete(self, prompt):
            return type('Response', (), {'text': "Paris is indeed the capital of France."})()

    # Register dependencies
    vector_store = MockVectorStore()
    llm = MockLLM()
    kitchen.register_dependency(DependencyType.VECTOR_STORE, vector_store)
    kitchen.register_dependency(DependencyType.LLM, llm)

    @kitchen.chat.handler("chat.rag", DependencyType.VECTOR_STORE, DependencyType.LLM)
    async def rag_handler(chat: ChatInput, vector_store, llm) -> ChatResponse:
        # Get the user's question
        question = chat.messages[-1].content
        
        # Search for relevant documents
        retriever = vector_store.as_retriever(similarity_top_k=2)
        nodes = retriever.retrieve(question)
        
        # Get response from LLM
        response = await llm.acomplete(question)
        
        # Return response with sources
        return ChatResponse(
            content=response.text,
            sources=[
                SourceNode(
                    text=node.node.text,
                    metadata=node.node.metadata,
                    score=node.score
                ) for node in nodes
            ]
        )

    # Test without requesting sources
    request = ChatCompletionRequest(
        messages=[Message(role="user", content="What is the capital of France?")],
        model="@test/chat.rag"
    )
    
    handler = kitchen.chat.get_task("chat.rag")
    response = await handler(request)
    
    assert response.choices[0].message.content == "Paris is indeed the capital of France."
    assert "metadata" not in response  # Sources not included when not requested

    # Test with sources requested
    request = ChatCompletionRequest(
        messages=[Message(role="user", content="What is the capital of France?")],
        model="@test/chat.rag",
        metadata={"include_sources": True}
    )
    
    response = await handler(request)
    
    assert response.choices[0].message.content == "Paris is indeed the capital of France."
    assert response.metadata is not None  # Check metadata field directly
    assert len(response.metadata["sources"]) == 2
    assert response.metadata["sources"][0]["text"] == "Paris is the capital of France"
    assert response.metadata["sources"][1]["text"] == "The Eiffel Tower is in Paris"
    assert response.metadata["sources"][1]["score"] == 0.85 