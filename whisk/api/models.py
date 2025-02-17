from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from fastapi import APIRouter, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import time
from ..dependencies import get_kitchen_app
from typing import Annotated
from ..kitchenai_sdk.http_schema import ModelResponse, ModelListResponse

class Model(BaseModel):
    """Represents a KitchenAI model (handler)"""
    id: str = Field(..., description="The model identifier in format @namespace-version/handler")
    object: str = Field("model", description="The object type, which is always 'model'")
    created: int = Field(..., description="The Unix timestamp (in seconds) when the model was created")
    owned_by: str = Field(..., description="The namespace that owns the model")
    handler_type: str = Field(..., description="The type of handler (chat, storage, embeddings, etc)")

class ModelList(BaseModel):
    """Response for listing available models"""
    object: str = Field("list", description="The object type, which is always 'list'")
    data: List[Model] = Field(default_factory=list, description="List of model objects")

# API Routes
router = APIRouter(
    prefix="/v1",
    tags=["Models"],
    responses={
        200: {
            "description": "Success",
            "content": {
                "application/json": {}
            }
        }
    }
)

def get_model_id(namespace: str, version: str, handler: str) -> str:
    """Generate model ID from namespace, version and handler"""
    return f"@{namespace}-{version}/{handler}"

def get_models_from_kitchen(app: KitchenAIApp) -> List[Model]:
    """Get all models from a KitchenAI app"""
    models = []
    created = int(time.time())  # Use current timestamp
    
    # Get all registered handlers from the app
    handlers = app.to_dict()
    
    # Add chat handlers
    for handler in handlers["chat_handlers"]:
        models.append(Model(
            id=get_model_id(app.namespace, app.version, handler),
            created=created,
            owned_by=app.namespace,
            handler_type="chat"
        ))
    
    # Add storage handlers
    for handler in handlers["storage_handlers"]:
        models.append(Model(
            id=get_model_id(app.namespace, app.version, handler),
            created=created,
            owned_by=app.namespace,
            handler_type="storage"
        ))
    
    # Add embedding handlers
    for handler in handlers["embed_handlers"]:
        models.append(Model(
            id=get_model_id(app.namespace, app.version, handler),
            created=created,
            owned_by=app.namespace,
            handler_type="embeddings"
        ))
    
    # Add agent handlers
    for handler in handlers["agent_handlers"]:
        models.append(Model(
            id=get_model_id(app.namespace, app.version, handler),
            created=created,
            owned_by=app.namespace,
            handler_type="agent"
        ))
    
    return models

@router.get("/models")
async def list_models():
    """List available models"""
    kitchen = get_kitchen_app()
    
    # Get all registered handlers from the app
    handlers = kitchen.to_dict()
    models = []
    created = int(time.time())
    
    # Add chat handlers
    for handler in handlers["chat_handlers"]:
        models.append(ModelResponse(
            id=f"@{kitchen.namespace}-{kitchen.version}/{handler}",
            created=created,
            owned_by=kitchen.namespace
        ))
    
    return ModelListResponse(data=models)

@router.options("/models")
async def models_options() -> Dict[str, Any]:
    """Handle OPTIONS request for CORS"""
    return {}

@router.get("/models/{model_id}", response_model=ModelResponse)
async def get_model(model_id: str):
    """Get model details"""
    kitchen = get_kitchen_app()
    
    # Parse model ID
    if not model_id.startswith("@"):
        raise HTTPException(status_code=404, detail="Invalid model ID format")
    
    namespace, handler = model_id[1:].split("/", 1)
    if namespace != kitchen.namespace:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # Check if handler exists in any taxonomy
    taxonomies = [kitchen.chat, kitchen.storage, kitchen.embeddings, kitchen.query]
    for taxonomy in taxonomies:
        if handler in taxonomy.get_handlers():
            return ModelResponse(
                id=model_id,
                object="model",
                created=None,
                owned_by=namespace
            )
    
    raise HTTPException(status_code=404, detail="Model not found")

@router.delete("/models/{model_id}", status_code=204)
async def delete_model(model_id: str):
    """Deletes a model (handler)"""
    # In this implementation, we don't allow deletion of handlers
    raise HTTPException(
        status_code=400,
        detail="Deletion of handlers is not supported"
    ) 