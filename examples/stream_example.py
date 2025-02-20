from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.schema import ChatInput, ChatResponse
from whisk.config import WhiskConfig, ServerConfig
from whisk.router import WhiskRouter
from typing import AsyncGenerator
import asyncio

# Create app with streaming handler
kitchen = KitchenAIApp(namespace="stream-example")

@kitchen.chat.handler("chat.stream")
async def stream_handler(chat: ChatInput) -> AsyncGenerator[ChatResponse, None]:
    """Example streaming chat handler that returns words one at a time"""
    # Simulate a response that streams word by word
    response = "Hello! I am a streaming chat bot. I will send this message word by word."
    words = response.split()
    
    for word in words:
        # Simulate some processing time
        await asyncio.sleep(0.5)
        # Yield each word as a ChatResponse
        yield ChatResponse(content=word + " ", role="assistant")

# Example of a more complex streaming handler with state
@kitchen.chat.handler("chat.interactive")
async def interactive_stream(chat: ChatInput) -> AsyncGenerator[ChatResponse, None]:
    """Interactive streaming chat handler that responds to user input"""
    # Get the user's message
    user_message = chat.messages[-1].content.lower()
    
    # Different responses based on user input
    if "hello" in user_message:
        responses = [
            "Hi there! ",
            "Nice to meet you! ",
            "I'm a streaming bot. ",
            "How can I help you today?"
        ]
    elif "help" in user_message:
        responses = [
            "I can help you with: ",
            "1. Streaming examples ",
            "2. Chat responses ",
            "3. Basic demonstrations"
        ]
    else:
        responses = [
            "I heard you say: ",
            user_message,
            ". ",
            "Try saying 'hello' or 'help' for more options!"
        ]
    
    # Stream each part of the response
    for response in responses:
        await asyncio.sleep(0.3)  # Simulate thinking time
        yield ChatResponse(content=response, role="assistant")

@kitchen.chat.handler("chat.completions")
async def completions(chat: ChatInput) -> ChatResponse:
    """Interactive streaming chat handler that responds to user input"""
    # Get the user's message
    user_message = chat.messages[-1].content.lower()
    
    # Different responses based on user input
    if "hello" in user_message:
        responses = [
            "Hi there! ",
            "Nice to meet you! ",
            "I'm a streaming bot. ",
            "How can I help you today?"
        ]
    elif "help" in user_message:
        responses = [
            "I can help you with: ",
            "1. Streaming examples ",
            "2. Chat responses ",
            "3. Basic demonstrations"
        ]
    else:
        responses = [
            "I heard you say: ",
            user_message,
            ". ",
            "Try saying 'hello' or 'help' for more options!"
        ]
    
    # Stream each part of the response
    return ChatResponse(content="I'm a regular chat response", role="assistant")

# Run the server
if __name__ == "__main__":
    config = WhiskConfig(server=ServerConfig(type="fastapi"))
    router = WhiskRouter(kitchen_app=kitchen, config=config)
    router.run(host="0.0.0.0", port=8000)
