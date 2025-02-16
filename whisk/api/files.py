from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/v1")

class FileObject(BaseModel):
    id: str
    object: str = "file"
    bytes: int
    created_at: int
    filename: str
    purpose: str

@router.post("/files")
async def upload_file(
    file: UploadFile = File(...),
    purpose: str = "fine-tune"
) -> FileObject:
    """Upload a file"""
    # Implementation here
    return FileObject(
        id="file-123",
        bytes=len(await file.read()),
        created_at=123,
        filename=file.filename,
        purpose=purpose
    )

@router.get("/files")
async def list_files() -> dict:
    """List uploaded files"""
    return {
        "object": "list",
        "data": []  # Implementation here
    } 