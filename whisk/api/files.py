from fastapi import APIRouter, UploadFile, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Annotated
from ..kitchenai_sdk.kitchenai import KitchenAIApp
import json
import time

router = APIRouter(
    prefix="/v1",
    tags=["Files"]
)

class FileObject(BaseModel):
    """OpenAI-compatible file object"""
    id: str
    object: str = "file"
    bytes: int
    created_at: int
    filename: str
    purpose: str = "assistants"

def get_kitchen_app() -> KitchenAIApp:
    """Dependency to get the KitchenAI app instance"""
    from whisk.examples.app import kitchen
    return kitchen

@router.post("/files", response_model=FileObject)
async def upload_file(
    file: UploadFile,
    kitchen: KitchenAIApp = Depends(get_kitchen_app)
):
    """Upload a file using FastAPI's UploadFile"""
    task = kitchen.storage.get_task("storage")
    if not task:
        raise HTTPException(status_code=404, detail="Storage handler not found")
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    # Process file through storage handler
    result = await task({
        "id": file.filename,
        "content": content,
        "metadata": {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": file_size
        }
    })
    
    # Return OpenAI-compatible response
    return FileObject(
        id=result.get("id", file.filename),
        bytes=file_size,
        created_at=int(time.time()),
        filename=file.filename
    )

@router.get("/files/{file_id}", response_model=FileObject)
async def get_file(
    file_id: str,
    kitchen: KitchenAIApp = Depends(get_kitchen_app)
):
    """Get file metadata by ID"""
    task = kitchen.storage.get_task("storage")
    if not task:
        raise HTTPException(status_code=404, detail="Storage handler not found")
    
    result = await task({
        "id": file_id,
        "action": "get"
    })
    
    if not result:
        raise HTTPException(status_code=404, detail=f"File {file_id} not found")
    
    return FileObject(
        id=result["id"],
        bytes=len(result.get("content", "")),
        created_at=result.get("created_at", int(time.time())),
        filename=result["metadata"]["filename"]
    )

@router.get("/files", response_model=dict)
async def list_files(
    kitchen: KitchenAIApp = Depends(get_kitchen_app)
) -> dict:
    """List all files"""
    task = kitchen.storage.get_task("storage")
    if not task:
        raise HTTPException(status_code=404, detail="Storage handler not found")
    
    result = await task({"action": "list"})
    
    files = []
    for file in result.get("files", []):
        files.append(FileObject(
            id=file["id"],
            bytes=file.get("size", 0),
            created_at=file.get("created_at", int(time.time())),
            filename=file["metadata"]["filename"]
        ))
    
    return {
        "object": "list",
        "data": files
    }

@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    kitchen: KitchenAIApp = Depends(get_kitchen_app)
):
    """Delete file by ID"""
    task = kitchen.storage.get_task("storage")
    if not task:
        raise HTTPException(status_code=404, detail="Storage handler not found")
    
    result = await task({
        "id": file_id,
        "action": "delete"
    })
    
    if not result:
        raise HTTPException(status_code=404, detail=f"File {file_id} not found")
    
    return {"deleted": True} 