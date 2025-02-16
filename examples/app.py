from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.schema import WhiskQuerySchema

kitchen = KitchenAIApp()

@kitchen.query.handler("chat")
async def handle_chat(query: WhiskQuerySchema):
    """This handler works for both NATS and FastAPI requests"""
    if query.stream:
        async def stream_gen():
            for chunk in ["Hello", " World"]:
                yield {"output": chunk}
        return {"stream_gen": stream_gen}
        
    return {"output": f"Response to: {query.query}"} 