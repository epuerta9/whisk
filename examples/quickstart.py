import logging
from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.schema import (
    ChatInput,
    ChatResponse,
)
from whisk.kitchenai_sdk.schema import StorageRequest, StorageResponse

from typing import Optional, Dict, Any
import time
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

# Initialize file_storage from existing files
def init_file_storage():
    """Initialize file storage from existing files in UPLOAD_DIR"""
    for file_path in UPLOAD_DIR.iterdir():
        if file_path.is_file():
            file_id = file_path.name
            # Try to reconstruct metadata
            metadata = {
                "filename": file_id,  # Use file_id as filename if original not known
                "content_type": "application/octet-stream",
                "size": file_path.stat().st_size,
                "purpose": "fine-tune"  # Default purpose
            }
            
            file_storage[file_id] = {
                "id": file_id,
                "path": str(file_path),
                "created_at": int(file_path.stat().st_mtime),
                "metadata": metadata
            }
            logger.info(f"Loaded existing file: {file_id}")

# Initialize storage on startup
init_file_storage()
logger.info(f"Initialized file_storage with {len(file_storage)} files")

@kitchen.chat.handler("quickstart")
async def handle_chat(data: ChatInput) -> ChatResponse:
    """Simple chat handler that echoes back the last message"""
    return ChatResponse(
        content=data.messages[-1].content, role="assistant", name="echo-app"
    )


@kitchen.storage.handler("storage")
async def handle_storage(data: StorageRequest) -> StorageResponse:
    """Example storage handler that implements basic file operations"""
    logger.info(f"Handling storage request: {data.action}")
    
    if data.action == "upload":
        # Generate unique file ID
        file_id = f"file-{int(time.time())}"
        
        # Store file metadata
        metadata = {
            "filename": data.filename,
            "content_type": data.metadata.get("content_type", "application/octet-stream"),
            "size": len(data.content),
            "purpose": data.purpose
        }
        
        # Save file content
        file_path = UPLOAD_DIR / file_id
        file_path.write_bytes(data.content)
        
        # Store in memory
        file_storage[file_id] = {
            "id": file_id,
            "path": str(file_path),
            "created_at": int(time.time()),
            "metadata": metadata
        }
        
        return StorageResponse(
            created_at=int(time.time()),
            metadata=metadata,
            deleted=False,
            file_id=file_id,
            filename=data.filename
        )
        
    elif data.action == "list":
        logger.info(f"Current file_storage: {file_storage}")
        files = [
            StorageResponse(
                created_at=file_data["created_at"],
                metadata=file_data["metadata"],
                deleted=False,
                file_id=file_id,
                filename=file_data["metadata"]["filename"]
            ) 
            for file_id, file_data in file_storage.items()
        ]
        logger.info(f"Returning files: {files}")
        return files
        
    elif data.action == "get":
        # Get file metadata
        file_data = file_storage.get(data.file_id)
        if not file_data:
            logger.warning(f"File not found in storage: {data.file_id}")
            return None
            
        return StorageResponse(
            created_at=file_data["created_at"],
            metadata=file_data["metadata"],
            deleted=False,
            file_id=file_data["id"],
            filename=file_data["metadata"]["filename"]
        )
        
    elif data.action == "delete":
        # Delete file
        if data.file_id not in file_storage:
            logger.warning(f"File not found for deletion: {data.file_id}")
            return None
            
        file_data = file_storage[data.file_id]
        file_path = Path(file_data["path"])
        
        # Delete physical file
        if file_path.exists():
            file_path.unlink()
            
        # Remove from storage
        del file_storage[data.file_id]
        
        return StorageResponse(
            created_at=file_data["created_at"],
            metadata=file_data["metadata"],
            deleted=True,
            file_id=data.file_id,
            filename=file_data["metadata"]["filename"]
        )
        
    else:
        raise ValueError(f"Unknown action: {data.action}")
