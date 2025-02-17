import pytest
from whisk.kitchenai_sdk.schema import WhiskStorageStatus, DependencyType
from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.http_schema import (  # Import from http_schema
    ChatCompletionRequest,
    Message
)

@pytest.mark.asyncio
async def test_query_handler_error(kitchen_app):
    @kitchen_app.chat.handler("chat.completions")
    async def handle_chat(request):
        raise ValueError("Test error")
    
    request = ChatCompletionRequest(
        messages=[{"role": "user", "content": "Hello"}],
        model="test-model"
    )
    
    with pytest.raises(ValueError):
        handler = kitchen_app.chat.get_task("chat.completions")
        await handler(request)

@pytest.mark.asyncio
async def test_storage_handler_error(kitchen_app, storage_data):
    @kitchen_app.storage.handler("storage")
    async def storage_handler(data):
        raise ValueError("Test error")
    
    handler = kitchen_app.storage.get_task("storage")
    with pytest.raises(ValueError):
        await handler(storage_data)

@pytest.mark.asyncio
async def test_invalid_dependency(kitchen_app):
    with pytest.raises(KeyError):
        kitchen_app.manager.get_dependency("invalid") 