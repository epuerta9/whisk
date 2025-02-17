import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from whisk.router import WhiskRouter
from whisk.config import WhiskConfig, ServerConfig, FastAPIConfig, NatsConfig, ClientConfig
from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.schema import WhiskQuerySchema
from whisk.kitchenai_sdk.http_schema import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatResponseMessage
)
from whisk.api.chat import router as chat_router, get_kitchen_app  # Import the router and get_kitchen_app

# Test fixtures
@pytest.fixture
def kitchen():
    app = KitchenAIApp()
    
    @app.chat.handler("test-model")
    async def handle_chat(request: ChatCompletionRequest):
        return ChatCompletionResponse(
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatResponseMessage(
                        role="assistant",
                        content="test response"
                    ),
                    finish_reason="stop"
                )
            ]
        )
    
    return app

@pytest.fixture
def fastapi_config():
    return WhiskConfig(
        server=ServerConfig(
            type="fastapi",
            fastapi=FastAPIConfig(
                host="0.0.0.0",
                port=8000,
                prefix="/v1"
            )
        ),
        nats=NatsConfig(
            url="nats://localhost:4222",
            user="test",
            password="test"
        ),
        client=ClientConfig(
            id="test_client"
        )
    )

# FastAPI-only tests
class TestFastAPIRouter:
    @pytest.fixture
    def app(self, kitchen, fastapi_config):
        # Create router directly with kitchen that has test handler
        router = WhiskRouter(kitchen, fastapi_config)
        return router.router  # Return the FastAPI app directly
    
    @pytest.fixture
    def client(self, kitchen):
        # Add test chat handler
        @kitchen.chat.handler("test-model")
        async def test_handler(request):
            return {
                "choices": [{
                    "message": {"role": "assistant", "content": "Test response"},
                    "finish_reason": "stop"
                }]
            }

        app = FastAPI()
        app.include_router(chat_router)  # Use imported router
        app.dependency_overrides[get_kitchen_app] = lambda: kitchen
        return TestClient(app)
    
    def test_chat_completions_endpoint(self, client):
        response = client.post(
            "/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "model": "test-model",
                "stream": False
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data
        assert len(data["choices"]) > 0
        assert "message" in data["choices"][0]
    
    def test_chat_completions_streaming(self, client):
        response = client.post(
            "/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "model": "test-model",
                "stream": True
            }
        )
        assert response.status_code == 200
        
        # Use iter_bytes() instead of iter_lines()
        chunks = [chunk.decode('utf-8') for chunk in response.iter_bytes()]
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.startswith("data: ")
