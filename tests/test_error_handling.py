import pytest
from whisk.kitchenai_sdk.schema import WhiskStorageStatus, DependencyType
from whisk.kitchenai_sdk.schema import ChatCompletionRequest, ChatMessage

@pytest.mark.asyncio
async def test_query_handler_error(kitchen):
    @kitchen.chat.handler("chat.completions")
    async def handle_chat(request: ChatCompletionRequest):
        raise ValueError("Test error")
    
    request = ChatCompletionRequest(
        messages=[ChatMessage(role="user", content="Hello")],
        model="test-model"
    )
    
    with pytest.raises(ValueError):
        handler = kitchen.chat.get_task("chat.completions")
        await handler(request)

@pytest.mark.asyncio
async def test_storage_handler_error(kitchen, storage_data):
    @kitchen.storage.handler("storage")
    async def storage_handler(data):
        raise ValueError("Test error")
    
    handler = kitchen.storage.get_task("storage")
    with pytest.raises(ValueError):
        await handler(storage_data)

def test_invalid_dependency(kitchen):
    with pytest.raises(KeyError):
        kitchen.manager.get_dependency(DependencyType.LLM) 