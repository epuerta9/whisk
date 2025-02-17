import pytest
from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.schema import (
    WhiskQuerySchema,
    WhiskQueryBaseResponseSchema,
    WhiskStorageSchema,
    WhiskStorageResponseSchema,
    DependencyType,
)
from whisk.kitchenai_sdk.http_schema import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatResponseMessage,
    Message
)

@pytest.fixture
def chat_app():
    app = KitchenAIApp(namespace="chat")
    
    @app.chat.handler("basic")
    async def basic_chat(request: ChatCompletionRequest):
        return ChatCompletionResponse(
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatResponseMessage(
                        role="assistant",
                        content="basic response"
                    ),
                    finish_reason="stop"
                )
            ]
        )
    
    @app.chat.handler("stream")
    async def stream_chat(request: ChatCompletionRequest):
        return ChatCompletionResponse(
            model=request.model,
            choices=[{
                "index": 0,
                "message": {"role": "assistant", "content": "stream response"},
                "finish_reason": "stop"
            }]
        )
    
    return app

@pytest.fixture
def rag_app():
    app = KitchenAIApp(namespace="rag")
    
    @app.chat.handler("search")
    async def rag_search(request: ChatCompletionRequest):
        return ChatCompletionResponse(
            model=request.model,
            choices=[{
                "index": 0,
                "message": {"role": "assistant", "content": "search response"},
                "finish_reason": "stop"
            }]
        )
    
    @app.storage.handler("ingest")
    async def rag_ingest(data: WhiskStorageSchema) -> WhiskStorageResponseSchema:
        return WhiskStorageResponseSchema(
            id=data.id,
            status="complete"
        )
    
    return app

def test_mount_app_merges_handlers(chat_app):
    """Test that mounting an app merges its handlers"""
    main_app = KitchenAIApp(namespace="main")
    main_app.mount_app("chat", chat_app)
    
    assert "chat.basic" in main_app.chat.list_tasks()

def test_mount_app_merges_dependencies(chat_app, rag_app):
    """Test that mounting apps correctly merges dependencies"""
    main_app = KitchenAIApp(namespace="main")
    
    # Register dependencies in sub-apps
    mock_llm = object()
    mock_store = object()
    chat_app.register_dependency(DependencyType.LLM, mock_llm)
    rag_app.register_dependency(DependencyType.VECTOR_STORE, mock_store)
    
    # Mount the sub-apps
    main_app.mount_app("chat", chat_app)
    main_app.mount_app("rag", rag_app)
    
    # Check dependencies were merged
    assert main_app.manager.has_dependency(DependencyType.LLM)
    assert main_app.manager.has_dependency(DependencyType.VECTOR_STORE)
    assert main_app.manager.get_dependency(DependencyType.LLM) is mock_llm
    assert main_app.manager.get_dependency(DependencyType.VECTOR_STORE) is mock_store

@pytest.mark.asyncio
async def test_mounted_handlers_execution(chat_app, rag_app):
    """Test that mounted handlers can be executed"""
    main_app = KitchenAIApp(namespace="main")
    main_app.mount_app("chat", chat_app)
    
    # Get and execute the mounted handler
    handler = main_app.chat.get_task("chat.basic")
    request = ChatCompletionRequest(
        messages=[Message(role="user", content="Hello")],
        model="test-model"
    )
    response = await handler(request)
    
    assert response.choices[0].message.content == "basic response"
    assert response.model == "test-model"

def test_mount_app_propagates_new_dependencies(chat_app, rag_app):
    """Test that new dependencies are propagated to mounted apps"""
    main_app = KitchenAIApp(namespace="main")
    main_app.mount_app("chat", chat_app)
    main_app.mount_app("rag", rag_app)
    
    # Register new dependency after mounting
    mock_llm = object()
    main_app.register_dependency(DependencyType.LLM, mock_llm)
    
    # Check dependency was propagated
    assert chat_app.manager.has_dependency(DependencyType.LLM)
    assert rag_app.manager.has_dependency(DependencyType.LLM)
    assert chat_app.manager.get_dependency(DependencyType.LLM) is mock_llm
    assert rag_app.manager.get_dependency(DependencyType.LLM) is mock_llm

def test_mount_app_namespace_isolation(chat_app, rag_app):
    """Test that mounted apps maintain their original namespaces"""
    main_app = KitchenAIApp(namespace="main")
    main_app.mount_app("chat", chat_app)
    main_app.mount_app("rag", rag_app)
    
    assert main_app.namespace == "main"
    assert chat_app.namespace == "chat"
    assert rag_app.namespace == "rag"

def test_to_dict_includes_mounted_handlers(chat_app, rag_app):
    """Test that to_dict includes mounted handlers"""
    main_app = KitchenAIApp(namespace="main")
    main_app.mount_app("chat", chat_app)
    main_app.mount_app("rag", rag_app)
    
    app_dict = main_app.to_dict()
    
    assert "chat.basic" in app_dict["chat_handlers"]
    assert "chat.stream" in app_dict["chat_handlers"]
    assert "rag.search" in app_dict["chat_handlers"]
    assert "rag.ingest" in app_dict["storage_handlers"] 