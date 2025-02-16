import pytest
from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.schema import (
    WhiskQuerySchema,
    WhiskStorageSchema,
    WhiskQueryBaseResponseSchema,
    WhiskStorageResponseSchema,
    ChatCompletionRequest,
    ChatCompletionResponse
)
from whisk.client import WhiskClient
from whisk.kitchenai_sdk.nats_schema import NatsRegisterMessage, BentoBox

@pytest.fixture
def app():
    app = KitchenAIApp(namespace="test")
    
    @app.chat.handler("chat.completions")
    async def handle_chat(request: ChatCompletionRequest):
        return ChatCompletionResponse(
            model=request.model,
            choices=[{
                "index": 0,
                "message": {"role": "assistant", "content": "test"},
                "finish_reason": "stop"
            }]
        )
    
    @app.storage.handler("storage")
    async def storage_handler(data: WhiskStorageSchema) -> WhiskStorageResponseSchema:
        return WhiskStorageResponseSchema(id=data.id, status="complete")
    
    return app

def test_to_dict_returns_lists(app):
    """Test that to_dict returns lists for handlers as required by NatsRegisterMessage"""
    result = app.to_dict()
    
    assert "chat_handlers" in result
    assert isinstance(result["chat_handlers"], list)
    assert "chat.completions" in result["chat_handlers"]
    assert "storage_handlers" in result
    assert isinstance(result["storage_handlers"], list)
    assert "storage" in result["storage_handlers"]

@pytest.mark.asyncio
async def test_client_registration(app):
    """Test that client registration works with the app's handler format"""
    client = WhiskClient(
        nats_url="nats://localhost:4222",
        kitchen=app
    )
    
    # Create BentoBox model first
    bento = BentoBox(**app.to_dict())
    
    # Then create registration message
    message = NatsRegisterMessage(
        client_id="test_client",
        version=app.version,
        name=app.namespace,
        bento_box=bento,
        client_type=app.client_type,
        client_description=app.client_description
    )
    
    assert isinstance(message.bento_box.chat_handlers, list)
    assert isinstance(message.bento_box.storage_handlers, list)
    assert "chat.completions" in message.bento_box.chat_handlers
    assert "storage" in message.bento_box.storage_handlers 