import pytest
from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.schema import (
    ChatCompletionRequest,
    ChatMessage,
    WhiskStorageSchema,
    WhiskEmbedSchema
)

@pytest.fixture
def kitchen():
    return KitchenAIApp(namespace="test")

def test_chat_handler(kitchen):
    """Test registering a chat handler"""
    
    @kitchen.chat.handler("chat.completions")
    async def handle_chat(request: ChatCompletionRequest):
        pass
    
    assert kitchen.chat.get_task("chat.completions") is not None

def test_storage_handler(kitchen):
    """Test registering a storage handler"""
    
    @kitchen.storage.handler("store")
    def handle_storage(data: WhiskStorageSchema):
        pass
    
    assert kitchen.storage.get_task("store") is not None

def test_embed_handler(kitchen):
    """Test registering an embed handler"""
    
    @kitchen.embeddings.handler("embed")
    def handle_embed(data: WhiskEmbedSchema):
        pass
    
    assert kitchen.embeddings.get_task("embed") is not None 