# Whisk 🥄⚡ 
**Effortless AI Microservices: Turn Your AI Logic into an OpenAI-Compatible API in Minutes.** 🚀

Whisk removes the boilerplate of writing AI microservices—so you can focus on what matters: your models, your data, and your business logic. Whether you're a **data scientist**, an **AI engineer**, or a **developer**, Whisk helps you spin up an OpenAI API–compatible service in just a few lines of code. 

---

## Table of Contents 
1. [Why Whisk?](#why-whisk)
2. [Key Features](#key-features)
3. [Quickstart](#quickstart)
   - [Installation](#installation)
   - [Minimal Chat Handler](#minimal-chat-handler)
   - [Running Your Whisk App](#running-your-whisk-app)
4. [Using Whisk with OpenWebUI](#using-whisk-with-openwebui)
5. [Jupyter Notebook Integration](#jupyter-notebook-integration)
6. [Examples](#examples)
   - [RAG-Enabled Chat Handler](#rag-enabled-chat-handler)
   - [File Storage](#file-storage)
7. [Advanced Usage](#advanced-usage)
   - [Custom FastAPI Setup](#custom-fastapi-setup)
   - [Dependency Injection](#dependency-injection)
8. [CLI Usage](#cli-usage)
9. [Configuration](#configuration)
10. [API Reference](#api-reference)
11. [Contributing](#contributing)
12. [License](#license)

---

## Why Whisk?

Traditional AI microservices can be time-consuming and repetitive to implement. With Whisk, you:
- **Experiment Faster**: Chat with your jupyter notebook. By creating AI entrypoints into your notebook, you can chat with your code in real time to see how it performs.
- **Eliminate Boilerplate**: You were going to build a FastAPI server for your AI code anyways, why not make it OpenAI compatible from the start? We already took care of that for you. They're super charged handlers specific for AI use cases.
- **Simplify your Business App**: AI moves fast, don't tie your business app with AI code just yet. Keep them loosely coupled with whisk so it's easy to swap out later.
- **Customization**: It's a FastAPI server we all know and love just AI focused. You can bring your own FastAPI application so it's even easier to get started.
- **Framework Agnostic**: It doesn't matter if it's llama index or langchain or crew. Whisk handles the server boilerplate for you and is strictly AI focused.
- **OpenAI Client Integrations**: Did we already mention it's OpenAI client compatible? This means you can use OpenWebUI to chat with your jupyter notebook or code.

---

## Demo

Chat with your Jupyter Notebook while you build! 

[Loom Video ](https://www.loom.com/share/92fc161d5b2248df8875e29c874b2aac?sid=4d588361-1a07-4079-ab84-70225dac9125)

## Quickstart

### Installation
```bash
pip install kitchenai-whisk
```

### Minimal Chat Handler

Create a file (e.g., `my_app.py`) with a simple echo handler:

```python
from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.schema import ChatInput, ChatResponse

# Initialize the app
kitchen = KitchenAIApp(namespace="whisk-example")

# Decorate your handler
@kitchen.chat.handler("chat.completions")
async def handle_chat(chat: ChatInput) -> ChatResponse:
    """Simple chat handler that echoes back the last message"""
    return ChatResponse(
        content=f"Echo: {chat.messages[-1].content}",
        role="assistant"
    )
```

### Running Your Whisk App

#### Option 1: Whisk CLI
```bash
# Serve using a module path: <module_name>:<kitchen_app_instance>
whisk serve my_app:kitchen --port 8000 --reload
```

#### Option 2: Programmatically
```python
# run_app.py
from whisk.router import WhiskRouter
from whisk.config import WhiskConfig, ServerConfig
from my_app import kitchen  # your KitchenAIApp

config = WhiskConfig(server=ServerConfig(type="fastapi"))
router = WhiskRouter(kitchen_app=kitchen, config=config)
router.run(host="0.0.0.0", port=8000)
```
Then just run:
```bash
python run_app.py
```

---

## Using Whisk with OpenWebUI

Spin up an **instant chat interface** with [OpenWebUI](https://github.com/OpenBMB/OpenWebUI):

1. **Pull and run OpenWebUI**:
   ```bash
   docker pull openwebui/openwebui

    docker run -d --network=host -v open-webui:/app/backend/data -e OLLAMA_BASE_URL=http://127.0.0.1:11434 --name open-webui --restart always ghcr.io/open-webui/open-webui:main

   ```

2. **Select your Whisk model** in OpenWebUI's model list and start chatting at:
   ```
   http://localhost:8000/v1
   ```

---

## Jupyter Notebook Integration

Experiment with your AI code **directly in Jupyter** using Whisk. Example:

```python
import nest_asyncio
nest_asyncio.apply()

from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.schema import ChatInput, ChatResponse
from whisk.config import WhiskConfig, ServerConfig
from whisk.router import WhiskRouter

kitchen = KitchenAIApp(namespace="notebook-example")

@kitchen.chat.handler("chat")
async def handle_chat(chat: ChatInput) -> ChatResponse:
    return ChatResponse(content="Hello from notebook!", role="assistant")

config = WhiskConfig(server=ServerConfig(type="fastapi"))
router = WhiskRouter(kitchen_app=kitchen, config=config)

# Run inside the notebook cell
router.run_in_notebook(host="0.0.0.0", port=8000)
```

---

## Examples

### RAG-Enabled Chat Handler

Combine your LLM with vector storage:

```python
@kitchen.chat.handler("chat.rag", DependencyType.VECTOR_STORE, DependencyType.LLM)
async def rag_handler(chat: ChatInput, vector_store, llm) -> ChatResponse:
    question = chat.messages[-1].content
    retriever = vector_store.as_retriever(similarity_top_k=2)
    nodes = retriever.retrieve(question)

    context = "\n".join(node.node.text for node in nodes)
    prompt = f"Answer based on context:\n{context}\n\nQuestion: {question}"

    response = await llm.acomplete(prompt)

    return ChatResponse(
        content=response.text,
        sources=[
            SourceNode(
                text=node.node.text,
                metadata=node.node.metadata,
                score=node.score
            )
            for node in nodes
        ]
    )
```
Now your requests to `/v1/chat/completions` can seamlessly retrieve relevant documents before generating a response.

### File Storage
Implement a custom file storage handler for anything from fine-tuning data to user uploads:

```python
from whisk.kitchenai_sdk.schema import StorageRequest, StorageResponse
import time
from pathlib import Path

@kitchen.storage.handler("storage")
async def handle_storage(data: StorageRequest) -> StorageResponse:
    # Example local file storage
    file_id = f"file-{int(time.time())}"
    file_path = Path("uploads") / file_id
    file_path.write_bytes(data.content)

    # Return structured response 
    return StorageResponse(
        file_id=file_id,
        filename=data.filename,
        created_at=int(time.time()),
        metadata={"purpose": data.purpose},
        deleted=False
    )
```
Use OpenAI-style file management methods to interact with it.

---

## Advanced Usage

### Custom FastAPI Setup

Attach Whisk routes to your own **FastAPI** application:

```python
from fastapi import FastAPI, Depends
from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.router import WhiskRouter
from whisk.config import WhiskConfig, ServerConfig

# Create Whisk app
kitchen = KitchenAIApp(namespace="custom-app")

@kitchen.chat.handler("chat.completions")
async def handle_chat(...):
    ...

# Create a custom FastAPI app
fastapi_app = FastAPI()

@fastapi_app.get("/health")
async def health_check():
    return {"status": "ok"}

# Hook Whisk into it
config = WhiskConfig(server=ServerConfig(type="fastapi"))
router = WhiskRouter(kitchen_app=kitchen, config=config, fastapi_app=fastapi_app)
router.run()
```

### Dependency Injection

Whisk's built-in dependency system lets you register external services, like Vector Stores or custom LLM clients:

```python
from whisk.kitchenai_sdk.schema import DependencyType

vector_store = MyVectorStore()
kitchen.register_dependency(DependencyType.VECTOR_STORE, vector_store)

@kitchen.chat.handler("chat.rag", DependencyType.VECTOR_STORE, DependencyType.LLM)
async def rag_handler(chat_input, vector_store, llm):
    # `vector_store` and `llm` are auto-injected
    ...
```

---

## CLI Usage

Create, serve, and manage Whisk projects:

```bash
# Initialize a new Whisk project
whisk init my-project

# Serve your app with a config file
whisk serve --config config.yaml

# Customize host/port 
whisk serve --host 0.0.0.0 --port 8080
```

---

## Configuration

Use a `whisk.yml` or `config.yaml` to define server settings:

```yaml
server:
  type: fastapi
  app_path: my_app.py:kitchen  # <module>:<kitchen_app>
  fastapi:
    host: 0.0.0.0
    port: 8000
    prefix: /v1

client:
  id: "my-app"
  type: "bento_box"
```

---

## API Reference

Whisk follows the OpenAI API structure:
- **`POST /v1/chat/completions`** - Chat completions  
- **`GET/POST /v1/files`** - File operations  
- **`GET /v1/models`** - List available models  

You can integrate with any existing OpenAI-compatible client. Just point it to your Whisk endpoint (e.g., `http://localhost:8000/v1`).

---

## Contributing

We welcome contributions! Please see our [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. Feel free to open issues for feature requests or bug reports.

---

## License

Whisk is licensed under the [Apache 2.0 License](LICENSE).  
© 2024 Whisk. All rights reserved.

---

**Get whisking**—and free yourself from the boilerplate of AI microservices!