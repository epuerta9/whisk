import logging
from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.http_schema import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatResponseMessage,
    FileUploadResponse
)
from typing import Optional, Dict, Any
import time
import json
import os
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize app
kitchen = KitchenAIApp(namespace="example-app")

# Simple in-memory file storage for example
file_storage = {}
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@kitchen.chat.handler("test-model")
async def handle_chat(request: ChatCompletionRequest):
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

@kitchen.file.handler("default")
async def handle_file(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle file operations with local storage"""
    action = request.get("action")
    logger.info(f"File handler called with action: {action}")
    
    if action == "upload":
        # Generate unique file ID
        file_id = f"file-{int(time.time())}"
        filename = request["filename"]
        content = request["content"]
        purpose = request["purpose"]
        
        # Save file metadata
        file_storage[file_id] = {
            "id": file_id,
            "filename": filename,
            "created_at": int(time.time()),
            "purpose": purpose,
            "bytes": len(content),
            "status": "processed"
        }
        
        # Save file content to disk
        file_path = UPLOAD_DIR / file_id
        file_path.write_bytes(content)
        
        logger.info(f"Uploaded file {filename} with ID {file_id}")
        return file_storage[file_id]
        
    elif action == "list":
        # Return list of all files
        return {
            "files": list(file_storage.values())
        }
        
    elif action == "get":
        # Get file metadata by ID
        file_id = request["id"]
        if file_id not in file_storage:
            raise ValueError(f"File not found: {file_id}")
            
        return file_storage[file_id]
        
    elif action == "delete":
        # Delete file and metadata
        file_id = request["id"]
        if file_id not in file_storage:
            raise ValueError(f"File not found: {file_id}")
            
        # Delete file from disk
        file_path = UPLOAD_DIR / file_id
        if file_path.exists():
            file_path.unlink()
            
        # Delete metadata
        metadata = file_storage.pop(file_id)
        logger.info(f"Deleted file {metadata['filename']} with ID {file_id}")
        
        return {
            "id": file_id,
            "object": "file",
            "deleted": True
        }
        
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