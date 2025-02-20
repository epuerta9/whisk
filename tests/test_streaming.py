import pytest
from fastapi.testclient import TestClient
import json
from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.schema import ChatInput, ChatResponse
from whisk.config import WhiskConfig, ServerConfig
from whisk.router import WhiskRouter
from typing import AsyncGenerator

@pytest.fixture
def app():
    kitchen = KitchenAIApp(namespace="test-stream")
    
    @kitchen.chat.handler("chat.completions")
    async def stream_handler(chat: ChatInput) -> AsyncGenerator[ChatResponse, None]:
        words = ["Hello", "world", "this", "is", "streaming"]
        for word in words:
            yield ChatResponse(content=word + " ", role="assistant")
    
    config = WhiskConfig(server=ServerConfig(type="fastapi"))
    router = WhiskRouter(kitchen_app=kitchen, config=config)
    return router.app

@pytest.mark.asyncio
async def test_streaming(app):
    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "@test-stream/chat.completions",
                "messages": [{"role": "user", "content": "Test message"}],
                "stream": True
            },
            headers={"Accept": "text/event-stream"}
        )
        
        assert response.status_code == 200
        # FastAPI adds charset=utf-8 by default, so check if content-type starts with text/event-stream
        assert response.headers["content-type"].startswith("text/event-stream")
        
        # Collect all streamed content
        content = []
        for line in response.iter_lines():
            # line might be bytes or str depending on the client
            if isinstance(line, bytes):
                line = line.decode('utf-8')
            if line:
                if line.startswith('data: ') and line != 'data: [DONE]':
                    chunk = json.loads(line.replace('data: ', ''))
                    if chunk['choices'][0]['delta'].get('content'):
                        content.append(chunk['choices'][0]['delta']['content'])
        
        # Verify streamed content
        expected = ["Hello ", "world ", "this ", "is ", "streaming "]
        assert content == expected

@pytest.mark.asyncio
async def test_streaming_format(app):
    """Test that streaming response follows OpenAI format"""
    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "@test-stream/chat.completions",
                "messages": [{"role": "user", "content": "Test message"}],
                "stream": True
            },
            headers={"Accept": "text/event-stream"}
        )
        
        # Get first chunk and verify format
        for line in response.iter_lines():
            # line might be bytes or str depending on the client
            if isinstance(line, bytes):
                line = line.decode('utf-8')
            if line:
                if line.startswith('data: ') and line != 'data: [DONE]':
                    chunk = json.loads(line.replace('data: ', ''))
                    assert "id" in chunk
                    assert chunk["object"] == "chat.completion.chunk"
                    assert "created" in chunk
                    assert "model" in chunk
                    assert len(chunk["choices"]) == 1
                    assert "delta" in chunk["choices"][0]
                    break 