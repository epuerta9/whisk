import logging
from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.schema import (
    ChatInput,
    ChatResponse,
    DependencyType,
    SourceNode,
    WhiskStorageSchema,
    WhiskStorageResponseSchema
)
from whisk.kitchenai_sdk.http_schema import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatResponseMessage
)
try:
    from llama_index.llms.openai import OpenAI
    from llama_index.embeddings.openai import OpenAIEmbedding
    from llama_index.core import VectorStoreIndex, Document
    from llama_index.core.vector_stores.simple import SimpleVectorStore
except ImportError:
    raise ImportError("Please install llama-index to use this example: pip install llama-index")
import time
import tempfile
from pathlib import Path
from llama_index.readers.file import PDFReader, DocxReader
from llama_index.core import StorageContext
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.core.extractors import TitleExtractor, QuestionsAnsweredExtractor

# Set up logging with proper configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize the app
kitchen = KitchenAIApp(namespace="whisk-example-app-2")

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
vector_store = SimpleVectorStore()
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# Create the index with the vector store
index = VectorStoreIndex.from_documents(
    documents,
    storage_context=storage_context,
    embed_model=embedding_model
)

# Register dependencies
kitchen.register_dependency(DependencyType.LLM, llm)
kitchen.register_dependency(DependencyType.VECTOR_STORE, index)

@kitchen.chat.handler("chat.completions")
async def handle_chat(request: ChatCompletionRequest):
    """Simple chat handler that forwards to OpenAI"""
    content = request.messages[-1].content
    
    # Handle special OpenWebUI requests after commands
    if "### Task:" in content and "### Chat History:" in content:
        chat_history = content.split("### Chat History:")[1].strip()
        
        # If this is a title/tag request after a command, return empty
        if any(cmd in chat_history for cmd in ["/help", "/show", "/capabilities", "/chat", "/file", "/eval"]):
            return ChatCompletionResponse(
                id=f"chatcmpl-{int(time.time())}",
                object="chat.completion",
                created=int(time.time()),
                model="gpt-3.5-turbo",
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message=ChatResponseMessage(
                            role="assistant",
                            content="{}"  # Return empty JSON
                        ),
                        finish_reason="stop"
                    )
                ]
            )
    
    # Forward to OpenAI for normal messages
    response = await llm.acomplete(content)
    
    return ChatCompletionResponse(
        model=request.model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatResponseMessage(
                    role="assistant",
                    content=response.text
                ),
                finish_reason="stop"
            )
        ]
    )

@kitchen.chat.handler("chat.rag", DependencyType.VECTOR_STORE, DependencyType.LLM)
async def rag_handler(chat: ChatInput, vector_store, llm) -> ChatResponse:
    """RAG-enabled chat handler"""
    
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

@kitchen.storage.handler("storage")
async def storage_handler(data: WhiskStorageSchema) -> WhiskStorageResponseSchema:
    """Storage handler for document ingestion"""
    try:
        # Parse model field if present: "@namespace-version/label" or just "label"
        label = data.model.split('/')[-1] if data.model else "default"
        if data.model and data.model.startswith('@'):
            # Format is "@namespace-version/label"
            namespace_version = data.model[1:].split('/')[0]  # Remove @ and get namespace-version
            namespace, version = namespace_version.split('-') if '-' in namespace_version else (namespace_version, None)
        else:
            # Just use the label
            namespace = None
            version = None

        if data.action == "list":
            return WhiskStorageResponseSchema(
                id=int(time.time()),
                name="list",
                files=[]
            )
            
        if data.action == "get":
            file_id = data.file_id.replace("file-", "")
            return WhiskStorageResponseSchema(
                id=int(file_id) if file_id.isdigit() else int(time.time()),
                name=data.file_id,
                metadata={}
            )
            
        if data.action == "delete":
            file_id = data.file_id.replace("file-", "")
            return WhiskStorageResponseSchema(
                id=int(file_id) if file_id.isdigit() else int(time.time()),
                name=data.file_id,
                deleted=True
            )
            
        # Handle upload
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file_path = Path(temp_dir) / data.filename
            
            # Write bytes data to temporary file
            with open(temp_file_path, 'wb') as f:
                f.write(data.content)
            
            # Select reader based on file extension
            file_ext = temp_file_path.suffix.lower()
            documents = []
            
            if file_ext == '.pdf':
                reader = PDFReader()
                documents = reader.load_data(temp_file_path)
            elif file_ext in ['.docx', '.doc']:
                reader = DocxReader()
                documents = reader.load_data(temp_file_path)
            else:
                content = temp_file_path.read_text()
                documents = [Document(text=content)]
            # Create a new vector store for this document
            doc_vector_store = SimpleVectorStore()
            doc_storage_context = StorageContext.from_defaults(
                vector_store=doc_vector_store
            )
            
            # Create index with the new vector store
            doc_index = VectorStoreIndex.from_documents(
                documents,
                storage_context=doc_storage_context,
                embed_model=embedding_model
            )
            logger.info(f"Doc index: {doc_index}")

            return WhiskStorageResponseSchema(
                id=int(time.time()),
                name=data.filename,
                label=label,  # Use parsed label
                metadata={
                    "namespace": namespace,
                    "version": version,
                    "model": data.model
                },
                created_at=int(time.time())
            )
            
    except Exception as e:
        logger.error(f"Error in storage handler: {str(e)}")
        raise
