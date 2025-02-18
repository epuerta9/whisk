from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.http_schema import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatResponseMessage
)
from whisk.kitchenai_sdk.schema import ChatInput, ChatResponse
from llama_index.core import (
    SimpleDirectoryReader,
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
)
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.agent import ReActAgent
from llama_index.llms.openai import OpenAI
from pathlib import Path
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the app
kitchen = KitchenAIApp(namespace="financial-analysis-agent")

@kitchen.chat.handler("chat.completions")
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

# Initialize indices and query engines
def init_query_engines():
    """Initialize or load query engines for financial documents"""
    try:
        # Try to load existing indices
        lyft_storage_context = StorageContext.from_defaults(persist_dir="./storage/lyft")
        uber_storage_context = StorageContext.from_defaults(persist_dir="./storage/uber")
        
        lyft_index = load_index_from_storage(lyft_storage_context)
        uber_index = load_index_from_storage(uber_storage_context)
        
    except:
        logger.info("Building new indices...")
        # Build new indices if loading fails
        lyft_docs = SimpleDirectoryReader(
            input_files=["./data/10k/lyft_2021.pdf"]
        ).load_data()
        uber_docs = SimpleDirectoryReader(
            input_files=["./data/10k/uber_2021.pdf"]
        ).load_data()

        lyft_index = VectorStoreIndex.from_documents(lyft_docs)
        uber_index = VectorStoreIndex.from_documents(uber_docs)

        # Persist indices
        lyft_index.storage_context.persist(persist_dir="./storage/lyft")
        uber_index.storage_context.persist(persist_dir="./storage/uber")

    # Create query engines
    lyft_engine = lyft_index.as_query_engine(similarity_top_k=3)
    uber_engine = uber_index.as_query_engine(similarity_top_k=3)

    return lyft_engine, uber_engine

# Initialize tools
def init_query_tools(lyft_engine, uber_engine):
    """Initialize query tools for the agent"""
    return [
        QueryEngineTool(
            query_engine=lyft_engine,
            metadata=ToolMetadata(
                name="lyft_10k",
                description=(
                    "Provides information about Lyft financials for year 2021. "
                    "Use a detailed plain text question as input to the tool."
                ),
            ),
        ),
        QueryEngineTool(
            query_engine=uber_engine,
            metadata=ToolMetadata(
                name="uber_10k",
                description=(
                    "Provides information about Uber financials for year 2021. "
                    "Use a detailed plain text question as input to the tool."
                ),
            ),
        ),
    ]

# Initialize agents
def init_agents(query_tools):
    """Initialize different types of agents"""
    llm = OpenAI(model="gpt-3.5-turbo")
    llm_instruct = OpenAI(model="gpt-3.5-turbo-instruct")

    agent = ReActAgent.from_tools(
        query_tools,
        llm=llm,
        verbose=True,
    )

    agent_instruct = ReActAgent.from_tools(
        query_tools,
        llm=llm_instruct,
        verbose=True,
    )

    return agent, agent_instruct

# Initialize everything on startup
lyft_engine, uber_engine = init_query_engines()
query_tools = init_query_tools(lyft_engine, uber_engine)
regular_agent, instruct_agent = init_agents(query_tools)

@kitchen.chat.handler("regular-agent")
async def handle_regular_agent(chat: ChatInput) -> ChatResponse:
    """Handle queries using the regular GPT-3.5-turbo agent"""
    question = chat.messages[-1].content
    response = await regular_agent.achat(question)
    return ChatResponse(
        content=str(response),
        role="assistant",
        name="financial-analysis-agent"
    )

@kitchen.chat.handler("instruct-agent")
async def handle_instruct_agent(chat: ChatInput) -> ChatResponse:
    """Handle queries using the GPT-3.5-turbo-instruct agent"""
    question = chat.messages[-1].content
    response = await instruct_agent.achat(question)
    return ChatResponse(
        content=str(response),
        role="assistant",
        name="financial-analysis-agent"
    )

# Optional context for more personality
FINANCIAL_CONTEXT = """
You are a veteran financial analyst with deep expertise in analyzing ride-sharing companies.
You provide detailed, data-driven insights while maintaining professional objectivity.
Base all your analyses on the provided financial documents and clearly indicate when you're making assumptions.
"""

if __name__ == "__main__":
    # Ensure OPENAI_API_KEY is set
    if "OPENAI_API_KEY" not in os.environ:
        api_key = input("Please enter your OpenAI API key: ")
        os.environ["OPENAI_API_KEY"] = api_key

