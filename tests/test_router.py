import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from whisk.router import WhiskRouter
from whisk.config import WhiskConfig, ServerConfig, FastAPIConfig, NatsConfig, ClientConfig
from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.schema import WhiskQuerySchema

# Test fixtures
@pytest.fixture
def kitchen():
    app = KitchenAIApp()
    
    @app.query.handler("chat")
    async def handle_chat(query: WhiskQuerySchema):
        if query.stream:
            async def stream_gen():
                for chunk in ["Hello", " World"]:
                    yield {"output": chunk}
            return {"stream_gen": stream_gen}
        return {"output": f"Response to: {query.query}"}
    
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
        fastapi_app = FastAPI()
        router = WhiskRouter(kitchen, fastapi_config, fastapi_app)
        router.mount()
        return fastapi_app
    
    @pytest.fixture
    def client(self, app):
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
