import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from whisk.api.files import router, get_kitchen_app
from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.schema import WhiskStorageResponseSchema
import tempfile
import json
from pathlib import Path

# Create test app and client
test_kitchen = KitchenAIApp(namespace="test-app")

# Create FastAPI app for testing
app = FastAPI()
app.include_router(router)

# Mock storage handler for testing
@test_kitchen.storage.handler("storage")
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

# Override dependency
def override_get_kitchen():
    return test_kitchen

app.dependency_overrides[get_kitchen_app] = override_get_kitchen

# Create test client
client = TestClient(app)

@pytest.fixture
def test_file():
    """Create a temporary test file"""
    with tempfile.NamedTemporaryFile(suffix=".txt") as f:
        f.write(b"test content")
        f.seek(0)
        yield f

def test_upload_file(test_file):
    """Test file upload endpoint"""
    extra_body = {
        "model": "@test-app-0.0.1/storage",
        "metadata": "key1=value1,key2=value2"
    }
    
    response = client.post(
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
    assert data["purpose"] == "test"
    assert data["status"] == "processed"

def test_list_files():
    """Test file listing endpoint"""
    response = client.get("/v1/files")
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    assert len(data["data"]) == 2
    assert data["data"][0]["id"] == "file-1"
    assert data["data"][1]["id"] == "file-2"
    assert data["data"][0]["filename"] == "test1.txt"
    assert data["data"][1]["filename"] == "test2.txt"

def test_get_file():
    """Test file retrieval endpoint"""
    response = client.get("/v1/files/file-123")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "file-123"
    assert data["filename"] == "test.txt"
    assert data["status"] == "processed"

def test_delete_file():
    """Test file deletion endpoint"""
    response = client.delete("/v1/files/file-123")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "file-123"
    assert data["deleted"] is True 