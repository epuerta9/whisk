import pytest
from whisk.kitchenai_sdk.schema import DependencyType
from whisk.kitchenai_sdk.base import DependencyManager
from whisk.kitchenai_sdk.schema import ChatCompletionRequest, ChatCompletionResponse

@pytest.mark.asyncio
async def test_dependency_registration(kitchen_app, mock_llm):
    kitchen_app.register_dependency(DependencyType.LLM, mock_llm)
    assert kitchen_app.manager.get_dependency(DependencyType.LLM) == mock_llm

@pytest.mark.asyncio
async def test_dependency_injection(kitchen_app, mock_llm, query_data):
    kitchen_app.register_dependency(DependencyType.LLM, mock_llm)
    
    @kitchen_app.chat.handler("test", DependencyType.LLM)
    async def test_handler(request, llm=None):
        assert llm == mock_llm
        return {"response": "test"}
        
    handler = kitchen_app.chat.get_task("test")
    await handler(ChatCompletionRequest(
        messages=[{"role": "user", "content": "test"}],
        model="test"
    ))

@pytest.mark.asyncio
async def test_missing_dependency(kitchen_app):
    @kitchen_app.chat.handler("test", DependencyType.LLM)
    async def handle_chat(request, llm=None):
        assert llm is None
        return {"response": "test"}

@pytest.mark.asyncio
async def test_multiple_dependencies(kitchen_app, mock_llm, mock_vector_store):
    kitchen_app.register_dependency(DependencyType.LLM, mock_llm)
    kitchen_app.register_dependency(DependencyType.VECTOR_STORE, mock_vector_store)
    
    @kitchen_app.chat.handler("test", DependencyType.LLM, DependencyType.VECTOR_STORE)
    async def handle_chat(request, llm=None, vector_store=None):
        assert llm == mock_llm
        assert vector_store == mock_vector_store
        return {"response": "test"} 