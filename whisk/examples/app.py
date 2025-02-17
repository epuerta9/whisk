import logging
from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.schema import (
    ChatInput,
    ChatResponse,
    DependencyType,
    SourceNode
)
try:
    from llama_index.llms.openai import OpenAI
    from llama_index.embeddings.openai import OpenAIEmbedding
    from llama_index.core import VectorStoreIndex, Document
except ImportError:
    raise ImportError("Please install llama-index to use this example: pip install llama-index")

# Set up logging with proper configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize the app
kitchen = KitchenAIApp(namespace="whisk-example-app")

# Initialize dependencies
llm = OpenAI(
    model="gpt-3.5-turbo",
    temperature=0.1
)

# Create a simple vector store with some documents
documents = [
    Document(text="The capital of France is Paris.", metadata={"source": "geography.txt"}),
    Document(text="The Eiffel Tower is 324 meters tall.", metadata={"source": "landmarks.txt"}),
    Document(text="Paris is known as the City of Light.", metadata={"source": "culture.txt"})
]

# Initialize vector store
embedding_model = OpenAIEmbedding()
vector_store = VectorStoreIndex.from_documents(
    documents,
    embed_model=embedding_model
)

# Register dependencies
kitchen.register_dependency(DependencyType.LLM, llm)
kitchen.register_dependency(DependencyType.VECTOR_STORE, vector_store)

@kitchen.chat.handler("chat.completions", DependencyType.LLM)
async def chat_handler(chat: ChatInput, llm) -> ChatResponse:
    """Simple chat completion handler"""
    # Get last message content
    prompt = chat.messages[-1].content
    logger.info(f"Simple chat prompt: {prompt}")
    
    # Get response from LLM
    response = await llm.acomplete(prompt)
    
    # Return simplified response
    return ChatResponse(content=response.text)

@kitchen.chat.handler("chat.rag", DependencyType.VECTOR_STORE, DependencyType.LLM)
async def rag_handler(chat: ChatInput, vector_store, llm) -> ChatResponse:
    """RAG-enabled chat handler"""
    logger.info("RAG handler called")
    
    # Get the user's question
    question = chat.messages[-1].content
    logger.info(f"RAG question: {question}")
    
    # Search for relevant documents
    retriever = vector_store.as_retriever(similarity_top_k=2)
    nodes = retriever.retrieve(question)
    
    # Create context from retrieved documents
    context = "\n".join(node.node.text for node in nodes)
    prompt = f"""Answer the question based on the following context:

Context:
{context}

Question: {question}

Answer:"""
    
    logger.info(f"RAG Prompt: {prompt}")
    
    # Get response from LLM
    response = await llm.acomplete(prompt)
    
    # Log retrieved sources
    logger.info(f"Retrieved sources: {[node.node.text for node in nodes]}")
    
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
