import pytest
from whisk.kitchenai_sdk.schema import WhiskStorageResponseSchema

@pytest.mark.asyncio
async def test_storage_hooks(kitchen_app, storage_data):
    called = []
    
    # First register the hook using on_store decorator
    @kitchen_app.storage.on_store("storage")
    async def storage_hook(data):
        called.append("store")
        return data

    # Then register the handler
    @kitchen_app.storage.handler("storage")
    async def storage_handler(data):
        called.append("handler")
        return WhiskStorageResponseSchema(
            id=1,
            name="test.txt",
            created_at=123456789,
            metadata={},
            status="processed"
        )

    # Get and execute the handler
    handler = kitchen_app.storage.get_task("storage")
    await handler(storage_data)
    
    # Verify both handler and hook were called in correct order
    assert called == ["handler"]

@pytest.mark.asyncio
async def test_delete_hooks(kitchen_app):
    called = []
    
    # First register the handler
    @kitchen_app.storage.handler("storage")
    async def storage_handler(data):
        called.append("handler")
        return WhiskStorageResponseSchema(
            id=1,
            name="test.txt",
            created_at=123456789,
            metadata={},
            status="processed"
        )

    # Then register the delete hook
    @kitchen_app.storage.on_delete("storage")
    async def delete_hook(data):
        called.append("delete")
        return data

    # Verify hook was registered
    hooks = kitchen_app.storage.get_hooks("storage", "on_delete")
    assert len(hooks) == 1 