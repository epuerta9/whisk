import pytest
from whisk.kitchenai_sdk.schema import WhiskEmbedResponseSchema

@pytest.mark.asyncio
async def test_basic_embed_handler(kitchen_app, embed_data):
    @kitchen_app.embeddings.handler("embed")
    async def embed_handler(data):
        assert data.text == embed_data.text
        assert data.metadata == embed_data.metadata
        return WhiskEmbedResponseSchema(
            metadata={"embedded": True}
        )
    
    handler = kitchen_app.embeddings.get_task("embed")
    response = await handler(embed_data)
    assert response.metadata["embedded"] == True

@pytest.mark.asyncio
async def test_embed_handler_with_token_counts(kitchen_app, embed_data, token_counts):
    @kitchen_app.embeddings.handler("embed")
    async def embed_handler(data):
        return WhiskEmbedResponseSchema(
            metadata={"embedded": True},
            token_counts=token_counts
        )
    
    handler = kitchen_app.embeddings.get_task("embed")
    response = await handler(embed_data)
    assert response.token_counts == token_counts 