from fastapi import APIRouter, UploadFile, HTTPException, Depends, File, Form
from typing import Optional, Dict, Any, Annotated, Callable
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

def get_storage_task(model: Optional[str]) -> Callable:
    """Get the appropriate storage task based on the model string
    
    Format: @namespace-version/handler
    Example: @quickstart-v1/default
    """
    kitchen = get_kitchen_app()
    logger.info(f"Getting storage task for model: {model}")
    
    if not model or not isinstance(model, str) or not model.startswith("@"):
        # Default to "storage" handler if no model specified
        handler = "storage"
        logger.info(f"Using default handler: {handler}")
    else:
        # Extract handler name from model field
        handler = model.split("/")[-1]
        logger.info(f"Using specified handler: {handler}")
    
    # Get the task
    task = kitchen.storage.get_task(handler)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Storage handler '{handler}' not found"
        )
    
    return task

@router.post("/files", response_model=FileResponse)
async def upload_file(
    file: UploadFile = File(...),
    purpose: str = Form("fine-tune"),
    model: str = Form("model"),
    extra_body: Optional[str] = Form(None)
):
    """Upload a file"""
    # Parse extra_body and metadata
    extra = json.loads(extra_body) if extra_body else {}
    metadata = parse_metadata(extra.get("metadata"))
    extra_model = extra.get("model")
    logger.info(f"Model: {model}")
    logger.info(f"Extra model: {extra_model}")
    
    # Get appropriate storage handler
    task = get_storage_task(model)
    content = await file.read()
    
    result = await task(StorageRequest(
        action="upload",
        content=content,
        filename=file.filename,
        purpose=purpose,
        model=model,
        metadata={
            **metadata,
            "content_type": file.content_type,
            "size": len(content)
        }
    ))
    
    return FileResponse(
        id=f"file-{result.file_id}",
        bytes=len(content),
        created_at=result.created_at,
        filename=result.filename,
        purpose=purpose,
        status="processed"
    )

@router.get("/files", response_model=FileListResponse)
async def list_files(
    purpose: Optional[str] = None,
    limit: int = 10000,
    order: str = "desc",
    after: Optional[str] = None,
    model: Optional[str] = None,
    extra_body: Optional[str] = None
):
    """List all files with pagination support"""
    # Parse extra_body to get model if provided
    if extra_body:
        try:
            extra = json.loads(extra_body)
            model = extra.get("model", model)
        except json.JSONDecodeError:
            pass
            
    logger.info(f"Listing files with model: {model}")
    task = get_storage_task(model)
    result = await task(StorageRequest(action="list"))
    logger.info(f"Got result: {result}")
    
    # Handle result as a list of StorageResponse objects
    files = [
        FileResponse(
            id=file.file_id,
            bytes=file.metadata.get("size", 0),
            created_at=file.created_at,
            filename=file.filename,
            purpose=file.metadata.get("purpose", "fine-tune"),
            status="processed"
        ) for file in result
    ]
    logger.info(f"Processed files: {files}")
    
    # Add pagination fields
    first_id = files[0].id if files else None
    last_id = files[-1].id if files else None
    
    response = FileListResponse(
        data=files,
        has_more=False,
        first_id=first_id,
        last_id=last_id,
        after=last_id if files else None
    )
    logger.info(f"Returning response: {response}")
    return response

@router.get("/files/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: str, 
    model: Optional[str] = None,
    metadata: Optional[str] = None,
    extra_body: Optional[str] = None
):
    """Get file metadata"""
    # Parse extra_body to get model and metadata if provided
    extra = {}
    logger.info(f"metadata: {metadata}")

    if extra_body:
        try:
            extra = json.loads(extra_body)
            model = extra.get("model", model)
        except json.JSONDecodeError:
            pass
        try:
            extra = json.loads(extra_body)
            metadata = extra.get("metadata", {})
        except json.JSONDecodeError:
            pass
            
    metadata = parse_metadata(metadata)
    logger.info(f"Getting file {file_id} with model: {model}, metadata: {metadata}")

    task = get_storage_task(model)
    try:
        result = await task(StorageRequest(
            action="get", 
            file_id=file_id,
            metadata=metadata
        ))
    except ValueError as e:
        logger.warning(f"File not found error: {str(e)}")
        raise HTTPException(
            status_code=404, 
            detail=f"File {file_id} not found"
        )
    
    if not result:
        raise HTTPException(
            status_code=404, 
            detail=f"File {file_id} not found"
        )
    
    return FileResponse(
        id=file_id,
        bytes=result.metadata.get("size", 0),
        created_at=result.created_at,
        filename=result.filename,
        purpose=result.metadata.get("purpose", "fine-tune"),
        status="processed"
    )

@router.delete("/files/{file_id}", response_model=FileDeleteResponse)
async def delete_file(file_id: str, model: Optional[str] = None):
    """Delete a file"""
    task = get_storage_task(model)
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
