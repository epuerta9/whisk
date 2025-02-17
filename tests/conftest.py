import pytest
from fastapi.testclient import TestClient
from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.config import WhiskConfig, ServerConfig
from whisk.router import WhiskRouter
from whisk.dependencies import set_kitchen_app
from whisk.kitchenai_sdk.schema import (
    WhiskQuerySchema,
    WhiskStorageSchema,
    WhiskEmbedSchema,
    DependencyType,
    TokenCountSchema,
    WhiskStorageResponseSchema
)

@pytest.fixture
def kitchen_app():
    """Create a test KitchenAI app"""
    app = KitchenAIApp(namespace="test-app")
    
    # Add test handlers
    @app.chat.handler("chat.completions")
    async def handle_chat(request):
        return {
            "id": "test-id",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Test response"
                }
            }]
        }
    
    @app.storage.handler("storage")
    async def handle_storage(request):
        return WhiskStorageResponseSchema(
            id=123,
            name="test.txt",
            created_at=123456789,
            metadata={},
            status="processed"
        )
    
    return app

@pytest.fixture
def test_client(kitchen_app):
    """Create a test client with the KitchenAI app configured"""
    config = WhiskConfig(server=ServerConfig(type="fastapi"))
    router = WhiskRouter(kitchen_app=kitchen_app, config=config)
    
    # Set up the app dependency
    set_kitchen_app(kitchen_app)
    
    return TestClient(router.app)

@pytest.fixture
def query_data():
    return WhiskQuerySchema(
        query="test query",
        label="query",
        metadata={"test": "metadata"}
    )

@pytest.fixture
def storage_data():
    return WhiskStorageSchema(
        id=1,
        name="test.txt",
        label="storage",
        data=b"test data",
        metadata={"test": "metadata"}
    )

@pytest.fixture
def embed_data():
    return WhiskEmbedSchema(
        label="embed",
        text="test text",
        metadata={"test": "metadata"}
    )

@pytest.fixture
def token_counts():
    return TokenCountSchema(
        embedding_tokens=100,
        llm_prompt_tokens=50,
        llm_completion_tokens=30,
        total_llm_tokens=80
    )

class MockLLM:
    async def acomplete(self, query, **kwargs):
        return type('Response', (), {'text': f"Response to: {query}"})()

@pytest.fixture
def mock_llm():
    return MockLLM()

class MockVectorStore:
    def add_documents(self, documents):
        pass
    
    def similarity_search(self, query):
        return []

@pytest.fixture
def mock_vector_store():
    return MockVectorStore() 