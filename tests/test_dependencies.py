import pytest
from whisk.kitchenai_sdk.schema import DependencyType
from whisk.kitchenai_sdk.base import DependencyManager
from whisk.kitchenai_sdk.schema import ChatCompletionRequest, ChatCompletionResponse

def test_dependency_registration(kitchen, mock_llm):
    kitchen.register_dependency(DependencyType.LLM, mock_llm)
    assert kitchen.manager.has_dependency(DependencyType.LLM)
    assert kitchen.manager.get_dependency(DependencyType.LLM) == mock_llm

def test_dependency_injection(kitchen, mock_llm, query_data):
    kitchen.register_dependency(DependencyType.LLM, mock_llm)
    
    @kitchen.chat.handler("test", DependencyType.LLM)
    async def handle_chat(request: ChatCompletionRequest, llm=None):
        assert llm is mock_llm
        return ChatCompletionResponse(
            model=request.model,
            choices=[{
                "index": 0,
                "message": {"role": "assistant", "content": "test"},
                "finish_reason": "stop"
            }]
        )

def test_missing_dependency(kitchen):
    @kitchen.chat.handler("test", DependencyType.LLM)
    async def handle_chat(request: ChatCompletionRequest, llm=None):
        assert llm is None
        return ChatCompletionResponse(
            model=request.model,
            choices=[{
                "index": 0,
                "message": {"role": "assistant", "content": "test"},
                "finish_reason": "stop"
            }]
        )

def test_multiple_dependencies(kitchen, mock_llm, mock_vector_store):
    kitchen.register_dependency(DependencyType.LLM, mock_llm)
    kitchen.register_dependency(DependencyType.VECTOR_STORE, mock_vector_store)
    
    @kitchen.chat.handler("test", DependencyType.LLM, DependencyType.VECTOR_STORE)
    async def handle_chat(request: ChatCompletionRequest, llm=None, vector_store=None):
        assert llm == mock_llm
        assert vector_store == mock_vector_store
        return ChatCompletionResponse(
            model=request.model,
            choices=[{
                "index": 0,
                "message": {"role": "assistant", "content": "test"},
                "finish_reason": "stop"
            }]
        ) 