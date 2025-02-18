from whisk.kitchenai_sdk.kitchenai import KitchenAIApp

from whisk.kitchenai_sdk.schema import (
    ChatInput,
    ChatResponse,
)

import logging


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize app
kitchen = KitchenAIApp(namespace="echo-app")

@kitchen.chat.handler("test-model")
async def handle_chat(data: ChatInput) -> ChatResponse:
    """Simple chat handler that echoes back the last message"""
    return ChatResponse(
        content=data.messages[-1].content, role="assistant", name="echo-app"
    )
