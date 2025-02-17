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
from whisk.api.chat import router as chat_router
from whisk.dependencies import get_kitchen_app, set_kitchen_app  # Import from dependencies instead

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
    def test_client(self, kitchen):
        # Register a chat handler with the expected name
        @kitchen.chat.handler("chat.completions")
        async def chat_handler(request):
            return ChatCompletionResponse(  # Use the proper response model
                id="test-id",
                object="chat.completion",
                created=123456789,
                model=request.model,
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message=ChatResponseMessage(
                            role="assistant", 
                            content="Test response"
                        ),
                        finish_reason="stop"
                    )
                ],
                usage={"total_tokens": 10}
            )

        app = FastAPI()
        app.include_router(chat_router)
        
        # Set up the kitchen app
        set_kitchen_app(kitchen)
        
        return TestClient(app)
    
    def test_chat_completions_endpoint(self, test_client):
        response = test_client.post(
            "/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "model": "@test-app-0.0.1/chat.completions",
                "stream": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "choices" in data
        assert len(data["choices"]) > 0
        assert "message" in data["choices"][0]
        assert data["choices"][0]["message"]["content"] == "Test response"

    def test_chat_completions_streaming(self, test_client):
        response = test_client.post(
            "/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "model": "@test-app-0.0.1/chat.completions",
                "stream": True
            }
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
