import pytest
from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.schema import (
    ChatMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    TokenCountSchema,
    ChatInput,
    ChatResponse
)
from whisk.kitchenai_sdk.schema import DependencyType

@pytest.fixture
def kitchen():
    return KitchenAIApp(namespace="test")

async def test_basic_chat_handler(kitchen):
    """Test basic chat completion handler"""
    
    @kitchen.chat.handler("chat.completions")
    async def handle_chat(request: ChatCompletionRequest):
        return ChatCompletionResponse(
            model=request.model,
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Test response"
                },
                "finish_reason": "stop"
            }]
        )

    request = ChatCompletionRequest(
        messages=[
            ChatMessage(role="user", content="Hello")
        ],
        model="test-model"
    )
    
    handler = kitchen.chat.get_task("chat.completions")
    response = await handler(request)
    
    assert response.choices[0]["message"]["content"] == "Test response"
    assert response.model == "test-model"

@pytest.mark.asyncio
async def test_chat_handler_with_llm(kitchen):
    """Test chat handler with LLM dependency"""

    class MockLLM:
        async def complete(self, messages):
            return "LLM response"

    llm = MockLLM()
    kitchen.register_dependency(DependencyType.LLM, llm)

    @kitchen.chat.handler("chat.completions", DependencyType.LLM)
    async def handle_chat(chat: ChatInput, llm: MockLLM) -> ChatResponse:
        response = await llm.complete(chat.messages)
        return ChatResponse(content=response)

    request = ChatCompletionRequest(
        messages=[ChatMessage(role="user", content="Hello")],
        model="test-model"
    )

    handler = kitchen.chat.get_task("chat.completions")
    response = await handler(request)
    assert response.choices[0]["message"]["content"] == "LLM response"

async def test_chat_handler_with_token_counts(kitchen):
    """Test chat handler with token counting"""
    
    @kitchen.chat.handler("chat.completions")
    async def handle_chat(request: ChatCompletionRequest):
        return ChatCompletionResponse(
            model=request.model,
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Test response"
                },
                "finish_reason": "stop"
            }],
            usage={
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        )

    request = ChatCompletionRequest(
        messages=[
            ChatMessage(role="user", content="Hello")
        ]
    )
    
    handler = kitchen.chat.get_task("chat.completions")
    response = await handler(request)
    
    assert response.usage["prompt_tokens"] == 10
    assert response.usage["completion_tokens"] == 5
    assert response.usage["total_tokens"] == 15 