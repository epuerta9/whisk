from whisk.kitchenai_sdk.kitchenai import KitchenAIApp

from whisk.kitchenai_sdk.schema import (
    ChatInput,
    ChatResponse,
    StorageRequest,
    StorageResponse,
)

import logging


import time
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize app
kitchen = KitchenAIApp(namespace="echo-app")

# Simple in-memory file storage for example
file_storage = {}
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@kitchen.chat.handler("test-model")
async def handle_chat(data: ChatInput) -> ChatResponse:
    """Simple chat handler that echoes back the last message"""
    return ChatResponse(
        content=data.messages[-1].content, role="assistant", name="echo-app"
    )


@kitchen.storage.handler("storage")
async def handle_file(data: StorageRequest) -> StorageResponse:
    """Handle file operations with local storage"""
    action = data.action

    if action == "upload":
        # Generate unique file ID
        file_id = f"file-{int(time.time())}"
        filename = data.filename
        content = data.content
        purpose = data.purpose

        # Save file metadata
        file_storage[file_id] = {
            "id": file_id,
            "filename": filename,
            "created_at": int(time.time()),
            "purpose": purpose,
            "bytes": len(content),
            "status": "processed",
        }

        # Save file content to disk
        file_path = UPLOAD_DIR / file_id
        file_path.write_bytes(content)

        return file_storage[file_id]

    elif action == "list":
        # Return list of all files
        return {"files": list(file_storage.values())}

    elif action == "get":
        # Get file metadata by ID
        file_id = data.id
        if file_id not in file_storage:
            raise ValueError(f"File not found: {file_id}")

        return file_storage[file_id]

    elif action == "delete":
        # Delete file and metadata
        file_id = data.id
        if file_id not in file_storage:
            raise ValueError(f"File not found: {file_id}")

        # Delete file from disk
        file_path = UPLOAD_DIR / file_id
        if file_path.exists():
            file_path.unlink()

        # Delete metadata
        metadata = file_storage.pop(file_id)

        return {"id": file_id, "object": "file", "deleted": True}

    else:
        raise ValueError(f"Unknown action: {action}")


# Optional: Add cleanup on shutdown
import atexit


@atexit.register
def cleanup():
    """Clean up uploaded files on shutdown"""
    if UPLOAD_DIR.exists():
        for file in UPLOAD_DIR.iterdir():
            file.unlink()
        UPLOAD_DIR.rmdir()
