import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from whisk.api.files import router
from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.schema import (
    WhiskStorageResponseSchema, 
    StorageResponse, 
    StorageRequest
)
from whisk.dependencies import get_kitchen_app, set_kitchen_app
import json
from io import BytesIO
import time

@pytest.fixture
def kitchen_app():
    """Create a test KitchenAI app with storage handler"""
    app = KitchenAIApp(namespace="test-app")
    
    # Keep track of deleted files
    deleted_files = set()
    
    @app.storage.handler("storage")
    async def mock_storage_handler(data: StorageRequest) -> StorageResponse:
        """Mock storage handler that returns predictable responses"""
        if data.action == "list":
            return [
                StorageResponse(
                    file_id="file-1",
                    filename="test1.txt",
                    created_at=1234567890,
                    metadata={
                        "size": 100,
                        "purpose": data.purpose or "fine-tune"
                    }
                ),
                StorageResponse(
                    file_id="file-2", 
                    filename="test2.txt",
                    created_at=1234567891,
                    metadata={
                        "size": 200,
                        "purpose": data.purpose or "fine-tune"
                    }
                )
            ]
        
        if data.action == "get":
            # Return None if file was deleted
            if data.file_id in deleted_files:
                return None
                
            return StorageResponse(
                file_id=data.file_id,
                filename="test.txt",
                created_at=1234567890,
                metadata={
                    "size": 100,
                    "purpose": data.purpose or "fine-tune"
                }
            )
        
        if data.action == "delete":
            # Track deleted files
            deleted_files.add(data.file_id)
            
            return StorageResponse(
                file_id=data.file_id,
                filename="test.txt",
                created_at=1234567890,
                deleted=True,
                metadata={
                    "size": 100,
                    "purpose": data.purpose or "fine-tune"
                }
            )
        
        # Handle upload
        return StorageResponse(
            file_id=f"file-{int(time.time())}",
            filename=data.filename,
            created_at=int(time.time()),
            metadata={
                **data.metadata,
                "size": len(data.content) if data.content else 0,
                "purpose": data.purpose or "fine-tune"
            }
        )
    
    return app

@pytest.fixture
def test_client(kitchen_app):
    """Create test client with initialized app"""
    app = FastAPI()
    app.include_router(router)
    
    # Initialize the app globally
    set_kitchen_app(kitchen_app)
    
    return TestClient(app)

def test_upload_file(test_client):
    """Test file upload endpoint"""
    test_file = BytesIO(b"test content")
    test_file.name = "test.txt"
    
    extra_body = {
        "model": "@test-app-0.0.1/storage",
        "metadata": "key1=value1,key2=value2"
    }
    
    response = test_client.post(
        "/v1/files",
        files={"file": ("test.txt", test_file)},
        data={
            "purpose": "test",
            "extra_body": json.dumps(extra_body)
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"].startswith("file-")
    assert data["filename"] == "test.txt"
    assert data["bytes"] > 0
    assert data["purpose"] == "test"
    assert data["status"] == "processed"

def test_list_files(test_client):
    """Test file listing endpoint"""
    response = test_client.get("/v1/files")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)
    
    if data["data"]:  # If there are files
        file = data["data"][0]
        assert "id" in file
        assert "filename" in file
        assert "bytes" in file
        assert "purpose" in file
        assert "status" in file

def test_get_file(test_client):
    """Test file retrieval endpoint"""
    # First upload a file
    test_file = BytesIO(b"test content")
    test_file.name = "test.txt"
    
    upload_response = test_client.post(
        "/v1/files",
        files={"file": ("test.txt", test_file)},
        data={"purpose": "test"}
    )
    assert upload_response.status_code == 200
    file_data = upload_response.json()
    file_id = file_data["id"]

    # Then retrieve it
    response = test_client.get(f"/v1/files/{file_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == file_id
    assert data["filename"] == "test.txt"
    assert data["bytes"] > 0
    assert data["status"] == "processed"

def test_delete_file(test_client):
    """Test file deletion endpoint"""
    # First upload a file
    test_file = BytesIO(b"test content")
    test_file.name = "test.txt"
    
    upload_response = test_client.post(
        "/v1/files",
        files={"file": ("test.txt", test_file)},
        data={"purpose": "test"}
    )
    assert upload_response.status_code == 200
    file_data = upload_response.json()
    file_id = file_data["id"]

    # Then delete it
    response = test_client.delete(f"/v1/files/{file_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == file_id
    assert data["deleted"] is True

    # Verify it's gone
    get_response = test_client.get(f"/v1/files/{file_id}")
    assert get_response.status_code == 404 