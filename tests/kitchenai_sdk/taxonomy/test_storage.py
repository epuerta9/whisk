import pytest
from whisk.kitchenai_sdk.taxonomy.storage import StorageTask
from whisk.kitchenai_sdk.schema import (
    WhiskStorageSchema,
    WhiskStorageResponseSchema
)

@pytest.fixture
def storage_task():
    """Create a storage task for testing"""
    return StorageTask(namespace="test")

async def test_register_handler(storage_task):
    """Test registering a storage handler"""
    @storage_task.handler("test")
    async def test_handler(data):
        return WhiskStorageResponseSchema(
            id=123,
            name="test.txt"
        )
    
    assert "test" in storage_task.handlers
    assert storage_task.handlers["test"] == test_handler

async def test_get_handler(storage_task):
    """Test getting a registered handler"""
    @storage_task.handler("test")
    async def test_handler(data):
        return WhiskStorageResponseSchema(
            id=123,
            name="test.txt"
        )
    
    handler = storage_task.get_handler("test")
    assert handler == test_handler
    assert storage_task.get_handler("nonexistent") is None

async def test_handler_execution(storage_task):
    """Test executing a storage handler"""
    @storage_task.handler("test")
    async def test_handler(data):
        return WhiskStorageResponseSchema(
            id=123,
            name=data.name,
            metadata=data.metadata
        )
    
    data = WhiskStorageSchema(
        id=1,
        name="test.txt",
        label="test",
        metadata={"key": "value"}
    )
    
    result = await storage_task.execute("test", data)
    assert result.id == 123
    assert result.name == "test.txt"
    assert result.metadata == {"key": "value"}

async def test_handler_validation(storage_task):
    """Test handler input/output validation"""
    @storage_task.handler("test")
    async def test_handler(data):
        # Return invalid response
        return {"id": "not_an_int"}
    
    data = WhiskStorageSchema(
        id=1,
        name="test.txt",
        label="test"
    )
    
    with pytest.raises(Exception):
        await storage_task.execute("test", data)

async def test_delete_handler(storage_task):
    """Test delete handler registration and execution"""
    delete_called = False
    
    @storage_task.on_delete("test")
    async def test_delete_handler(data):
        nonlocal delete_called
        delete_called = True
    
    data = WhiskStorageSchema(
        id=1,
        name="test.txt",
        label="test"
    )
    
    await storage_task.execute_delete("test", data)
    assert delete_called 