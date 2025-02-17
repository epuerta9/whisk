import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from whisk.api.files import router
from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.schema import WhiskStorageResponseSchema
from whisk.dependencies import get_kitchen_app, set_kitchen_app
import json
from io import BytesIO

@pytest.fixture
def kitchen_app():
    """Create a test KitchenAI app with storage handler"""
    app = KitchenAIApp(namespace="test-app")
    
    @app.storage.handler("storage")
    async def mock_storage_handler(data):
        """Mock storage handler that returns predictable responses"""
        if data.action == "list":
            return WhiskStorageResponseSchema(
                id=12345,
                name="list",
                files=[
                    WhiskStorageResponseSchema(
                        id=1,
                        name="test1.txt",
                        metadata={"size": 100},
                        created_at=1234567890
                    ),
                    WhiskStorageResponseSchema(
                        id=2,
                        name="test2.txt",
                        metadata={"size": 200},
                        created_at=1234567891
                    )
                ]
            )
        
        if data.action == "get":
            return WhiskStorageResponseSchema(
                id=int(data.file_id.replace("file-", "")),
                name="test.txt",
                metadata={"size": 100},
                created_at=1234567890
            )
        
        if data.action == "delete":
            return WhiskStorageResponseSchema(
                id=int(data.file_id.replace("file-", "")),
                name=data.file_id,
                deleted=True
            )
        
        # Handle upload
        return WhiskStorageResponseSchema(
            id=12345,
            name=data.filename,
            metadata=data.metadata,
            created_at=1234567890
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
    assert data["filename"] == "test.txt"

def test_list_files(test_client):
    """Test file listing endpoint"""
    response = test_client.get("/v1/files")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) > 0

def test_get_file(test_client):
    """Test get file endpoint"""
    response = test_client.get("/v1/files/file-1")  # Use correct file ID format
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "file-1"

def test_delete_file(test_client):
    """Test delete file endpoint"""
    response = test_client.delete("/v1/files/file-1")  # Use correct file ID format
    assert response.status_code == 200
    data = response.json()
    assert data["deleted"] is True 