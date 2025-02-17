import logging
from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.schema import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    WhiskStorageSchema,
    WhiskStorageResponseSchema,
    WhiskEmbedSchema,
    WhiskEmbedResponseSchema
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
async def chat_handler(request: ChatCompletionRequest) -> ChatCompletionResponse:
    """Chat completion handler"""
    response = await llm.acomplete(request.messages[-1].content)
    return ChatCompletionResponse(
        model=request.model,
        choices=[{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": response.text
            },
            "finish_reason": "stop"
        }]
    )

@kitchen.storage.handler("storage")
async def storage_handler(data: WhiskStorageSchema) -> WhiskStorageResponseSchema:
    """Storage handler"""
    return WhiskStorageResponseSchema(
        id=data.id,
        status="complete"
    )

@kitchen.embeddings.handler("embed")
async def embed_handler(data: WhiskEmbedSchema) -> WhiskEmbedResponseSchema:
    """Embedding handler"""
    return WhiskEmbedResponseSchema(
        id=data.id,
        embeddings=[[0.1, 0.2, 0.3]]  # Example embeddings
    )
