# Whisk 🥄⚡

**"Whisk – Effortless AI Microservices: Turn Your AI Logic into an OpenAI-Compatible API in Minutes."** 🚀

Whisk is a flexible runtime framework for building AI applications with support for chat, file storage, and more. It provides a FastAPI-based HTTP API and easy-to-use handler system so you can focus on building your AI logic. 

* OpenWebUI compatible
* OpenAI compatible
* FastAPI compatible
* Dependency injection
* Easy to use
* Easy to deploy
* Easy to scale

## Installation

```bash
pip install kitchenai-whisk
```

## Quick Start

Turn your AI functions into model-like APIs with a simple decorator:

```python
from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.http_schema import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatResponseMessage
)

# Initialize the app
kitchen = KitchenAIApp(namespace="whisk-example-app")

@kitchen.chat.handler("chat.completions")
async def handle_chat(request: ChatCompletionRequest) -> ChatCompletionResponse:
    """Simple chat handler that echoes back the last message"""
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
```

Now your handler can be called like a regular OpenAI endpoint:

```python
response = client.chat.completions.create(
    model="@whisk-example-app-0.0.1/chat.completions",
    messages=[{"role": "user", "content": "Hello!"}],
    metadata={"user_id": "123"},
)
```

### RAG-enabled Chat Handler

```python
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
```

### Storage Handler

```python
from whisk.kitchenai_sdk.schema import (
    WhiskStorageSchema,
    WhiskStorageResponseSchema
)

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
```

```python
import json

from whisk.kitchenai_sdk.http_schema import FileExtraBody   

file_extra_body = FileExtraBody(
    model="@whisk-example-app-0.0.1/storage",
    metadata="user_id=123,other_key=value"  # Changed to string format
)

response = client.files.create(
    file=open("README.md", "rb"),
    purpose="chat",
    extra_body=file_extra_body.model_dump()
)
print(response)
```

## Running Your App

There are several ways to run your Whisk application:

### 1. Using the CLI with Module Path

The most flexible way is to use the CLI with a module path to your app:

```bash
# Format: whisk serve module.path:app_name
whisk serve my_app.main:kitchen

# With options
whisk serve my_app.main:kitchen --port 8080 --reload
```

You can also specify the app path in your config file:

```yaml
# whisk.yml
server:
  type: fastapi
  app_path: my_app.main:kitchen  # Module path to your KitchenAI app
  fastapi:
    host: 0.0.0.0
    port: 8000
```

Then simply run:
```bash
whisk serve
```

The CLI argument takes precedence over the config file setting.

### 2. Running Programmatically

```python
# In a script
from whisk.router import WhiskRouter
from whisk.config import WhiskConfig, ServerConfig

# Create router
router = WhiskRouter(kitchen_app, config)

# Run with custom host/port
router.run(host="0.0.0.0", port=8000)
```

### 3. Using Your Own FastAPI App

```python
from fastapi import FastAPI
from whisk.router import WhiskRouter

# Create your FastAPI app
app = FastAPI()

# Create router with your app
router = WhiskRouter(
    kitchen_app=kitchen_app,
    config=config,
    fastapi_app=app
)

# Run the server
router.run()
```

## Customizing FastAPI

### Using Your Own FastAPI App

```python
from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordBearer
from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.config import WhiskConfig
from whisk.router import WhiskRouter

# Create your KitchenAI app
kitchen_app = KitchenAIApp(namespace="my-app")

# Add your handlers
@kitchen.chat.handler("chat.completions")
async def handle_chat(request: ChatCompletionRequest) -> ChatCompletionResponse:
    """Simple chat handler that echoes back the last message"""
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

# Create your FastAPI app with custom auth
fastapi_app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@fastapi_app.post("/token")
async def login():
    return {"access_token": "secret"}

async def get_current_user(token: str = Depends(oauth2_scheme)):
    if token != "secret":
        raise HTTPException(status_code=401)
    return {"user": token}

# Add custom routes before Whisk setup
@fastapi_app.get("/custom", dependencies=[Depends(get_current_user)])
async def custom_route():
    return {"message": "Authenticated route"}

# Create WhiskRouter with your FastAPI app
config = WhiskConfig(server=ServerConfig(type="fastapi"))
router = WhiskRouter(
    kitchen_app=kitchen_app, 
    config=config,
    fastapi_app=fastapi_app  # Pass your custom app
)

# Run the server
router.run()
```

### Using Setup Callbacks

```python
def before_setup(app: FastAPI):
    """Add routes/middleware before Whisk setup"""
    # Add auth
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
    
    @app.post("/token")
    async def login():
        return {"access_token": "secret"}

    # Add custom middleware
    @app.middleware("http")
    async def add_custom_header(request, call_next):
        response = await call_next(request)
        response.headers["Custom"] = "Value"
        return response

def after_setup(app: FastAPI):
    """Add routes after Whisk setup"""
    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

# Create router with callbacks
router = WhiskRouter(
    kitchen_app=kitchen_app,
    config=config,
    before_setup=before_setup,  # Runs before Whisk routes
    after_setup=after_setup    # Runs after Whisk routes
)

# Access FastAPI app directly if needed
app = router.app
```

### Running Programmatically

```python
# In a script
from whisk.router import WhiskRouter
from whisk.config import WhiskConfig, ServerConfig

# Create router
router = WhiskRouter(kitchen_app, config)

# Run with custom host/port
router.run(host="0.0.0.0", port=8000)

```

## Dependencies

Whisk supports dependency injection for handlers:

```python
from whisk.kitchenai_sdk.schema import DependencyType

# Register dependency
vector_store = MyVectorStore()
app.register_dependency(DependencyType.VECTOR_STORE, vector_store)

# Use in handler
@kitchen.chat.handler("chat.rag", DependencyType.VECTOR_STORE, DependencyType.LLM)
async def rag_handler(chat: ChatInput, vector_store, llm) -> ChatResponse:
    # vector_store is automatically injected
    docs = await vector_store.search(request.messages[-1].content)
    return {"response": f"Found docs: {docs}"}
```

## Jupyter Notebook Usage

```python
import nest_asyncio
nest_asyncio.apply()

# Create and run
router = WhiskRouter(kitchen, config)
router.run()
```

## CLI Usage

```bash
# Start server
whisk serve --config config.yaml

# Initialize new project
whisk init my-project

# Run with custom host/port
whisk serve --host 0.0.0.0 --port 8080
```

## Configuration

```yaml
# config.yaml
server:
  type: fastapi
  fastapi:
    host: 0.0.0.0
    port: 8000
    prefix: /v1

client:
  id: my-app
  type: bento_box
```



## API Reference

The API follows OpenAI's API structure:

- `/v1/chat/completions` - Chat completions
- `/v1/files` - File operations
- `/v1/models` - List available models

## Contributing

Contributions welcome! Please read our [contributing guidelines](CONTRIBUTING.md).

## License

Apache 2.0 License

Copyright (c) 2024 Whisk

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
