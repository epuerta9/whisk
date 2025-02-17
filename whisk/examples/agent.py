from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.http_schema import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatResponseMessage
)

# Initialize the app
kitchen = KitchenAIApp(namespace="whisk-python-script-modified")

@kitchen.chat.handler("chat.completions,new")
async def handle_chat(request: ChatCompletionRequest) -> ChatCompletionResponse:
    """Simple chat handler that echoes back the last message"""


    print(request)
    return ChatCompletionResponse(
        model=request.model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatResponseMessage(
                    role="assistant",
                    content=f"Echo: {request.messages[-1].content}"
                ),
                finish_reason="stop"
            )
        ]
    )


from whisk.kitchenai_sdk.schema import (
    ChatInput, 
    ChatResponse,
    DependencyType,
    SourceNode
)

@kitchen.chat.handler("chat.rag", DependencyType.VECTOR_STORE, DependencyType.LLM)
async def rag_handler(chat: ChatInput, vector_store, llm) -> ChatResponse:
    """RAG-enabled chat handler"""
    # Get the user's question
    question = chat.messages[-1].content
    
    # Search for relevant documents
    retriever = vector_store.as_retriever(similarity_top_k=2)
    nodes = retriever.retrieve(question)
    
    # Create context from retrieved documents
    context = "\n".join(node.node.text for node in nodes)
    prompt = f"""Answer based on context: {context}\nQuestion: {question}"""
    
    # Get response from LLM
    response = await llm.acomplete(prompt)
    
    # Return response with sources
    return ChatResponse(
        content=response.text,
        sources=[
            SourceNode(
                text=node.node.text,
                metadata=node.node.metadata,
                score=node.score
            ) for node in nodes
        ]
    )


from whisk.kitchenai_sdk.schema import (
    WhiskStorageSchema,
    WhiskStorageResponseSchema
)
import time

@kitchen.storage.handler("storage")
async def storage_handler(data: WhiskStorageSchema) -> WhiskStorageResponseSchema:
    """Storage handler for document ingestion"""
    if data.action == "list":
        return WhiskStorageResponseSchema(
            id=int(time.time()),
            name="list",
            files=[]
        )
        
    if data.action == "upload":
        return WhiskStorageResponseSchema(
            id=int(time.time()),
            name=data.filename,
            label=data.model.split('/')[-1],
            metadata={
                "namespace": data.model.split('/')[0],
                "model": data.model
            },
            created_at=int(time.time())
        )