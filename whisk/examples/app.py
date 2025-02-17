import logging
from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.schema import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    WhiskStorageSchema,
    WhiskStorageResponseSchema,
    WhiskEmbedSchema,
    WhiskEmbedResponseSchema,
    ChatInput,
    ChatResponse
)
try:
    from llama_index.llms.openai import OpenAI
except ImportError:
    raise ImportError("Please install llama-index to use this example: pip install llama-index")

# Initialize the app
kitchen = KitchenAIApp(namespace="whisk-example-app")

# Initialize LLM
llm = OpenAI(
    model="gpt-3.5-turbo",
    temperature=0.1
)

# Set up logging
logger = logging.getLogger(__name__)

@kitchen.chat.handler("chat.completions")
async def chat_handler(chat: ChatInput) -> ChatResponse:
    """Chat completion handler"""
    # Get last message content
    prompt = chat.messages[-1].content
    
    # Get response from LLM
    response = await llm.acomplete(prompt)
    
    # Return simplified response
    return ChatResponse(content=response.text)

@kitchen.storage.handler("storage")
async def storage_handler(data: WhiskStorageSchema) -> WhiskStorageResponseSchema:
    """Storage handler"""
    return WhiskStorageResponseSchema(
        id=data.id,
        status="complete"
    )
