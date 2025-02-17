from fastapi import APIRouter, UploadFile, HTTPException, Depends, File, Form
from typing import Optional, Dict, Any, Annotated
from ..kitchenai_sdk.kitchenai import KitchenAIApp
from ..kitchenai_sdk.http_schema import FileResponse, FileListResponse, FileDeleteResponse
from ..kitchenai_sdk.schema import StorageRequest
import time
import json
from ..dependencies import get_kitchen_app

router = APIRouter(prefix="/v1", tags=["Files"])
import logging
logger = logging.getLogger(__name__)

def parse_metadata(metadata_str: Optional[str]) -> Dict[str, str]:
    """Parse metadata string into dictionary"""
    if not metadata_str:
        return {}
    try:
        return dict(item.split("=") for item in metadata_str.split(","))
    except Exception as e:
        logger.warning(f"Failed to parse metadata string: {metadata_str}")
        return {}


@router.post("/files", response_model=FileResponse)
async def upload_file(
    file: UploadFile = File(...),
    purpose: str = Form("fine-tune"),
    extra_body: Optional[str] = Form(None)
):
    """Upload a file"""
    kitchen_app = get_kitchen_app()  # Get app directly
    task = kitchen_app.storage.get_task("storage")
    if not task:
        raise HTTPException(status_code=404, detail="Storage handler not found")

    content = await file.read()
    
    # Parse extra_body and metadata
    extra = json.loads(extra_body) if extra_body else {}
    metadata = parse_metadata(extra.get("metadata"))
    model = extra.get("model")
    
    result = await task(StorageRequest(
        action="upload",
        content=content,
        filename=file.filename,
        purpose=purpose,
        model=model,
        metadata={
            **metadata,  # Include parsed metadata
            "content_type": file.content_type,
            "size": len(content)
        }
    ))
    
    return FileResponse(
        id=f"file-{result.id}",
        bytes=len(content),
        created_at=result.created_at,
        filename=file.filename,
        purpose=purpose,
        status="processed"
    )


@router.get("/files", response_model=FileListResponse)
async def list_files(
    purpose: Optional[str] = None,
    limit: int = 10000,
    order: str = "desc",
    after: Optional[str] = None
):
    """List all files with pagination support"""
    kitchen_app = get_kitchen_app()  # Get app directly
    task = kitchen_app.storage.get_task("storage")
    if not task:
        raise HTTPException(status_code=404, detail="Storage handler not found")
    
    result = await task(StorageRequest(action="list"))
    
    files = [
        FileResponse(
            id=f"file-{file.id}",
            bytes=file.metadata.get("size", 0),
            created_at=file.created_at,
            filename=file.name,
            purpose=file.metadata.get("purpose", "fine-tune"),
            status="processed"
        ) for file in result.files
    ]
    
    # Add pagination fields
    first_id = files[0].id if files else None
    last_id = files[-1].id if files else None
    
    return FileListResponse(
        data=files,
        has_more=False,  # Implement real pagination if needed
        first_id=first_id,
        last_id=last_id,
        after=last_id if files else None
    )


@router.get("/files/{file_id}", response_model=FileResponse)
async def get_file(file_id: str):
    """Get file metadata"""
    kitchen_app = get_kitchen_app()  # Get app directly
    task = kitchen_app.storage.get_task("storage")
    if not task:
        raise HTTPException(status_code=404, detail="Storage handler not found")

    result = await task(StorageRequest(action="get", file_id=file_id))

    if not result:
        raise HTTPException(status_code=404, detail=f"File {file_id} not found")

    return FileResponse(
        id=file_id,
        bytes=result.metadata.get("size", 0),
        created_at=result.created_at or int(time.time()),  # Use result timestamp or current time
        filename=result.name,
        purpose=result.metadata.get("purpose", "fine-tune"),
        status="processed"
    )


@router.delete("/files/{file_id}", response_model=FileDeleteResponse)
async def delete_file(file_id: str):
    """Delete a file"""
    kitchen_app = get_kitchen_app()  # Get app directly
    task = kitchen_app.storage.get_task("storage")
    if not task:
        raise HTTPException(status_code=404, detail="Storage handler not found")
    
    result = await task(StorageRequest(
        action="delete",
        file_id=file_id
    ))
    
    if not result or not result.deleted:
        raise HTTPException(status_code=404, detail=f"File {file_id} not found")
    
    return FileDeleteResponse(
        id=file_id,
        deleted=True
    )
