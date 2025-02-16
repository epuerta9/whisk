from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/v1")

class Model(BaseModel):
    id: str
    object: str = "model"
    owned_by: str
    permission: List[dict] = []

@router.get("/models")
async def list_models() -> dict:
    """List available models"""
    return {
        "object": "list",
        "data": [
            {
                "id": "whisk-default",
                "object": "model",
                "owned_by": "kitchen-ai",
                "permission": []
            }
        ]
    }

@router.get("/models/{model_id}")
async def get_model(model_id: str) -> Model:
    """Get model information"""
    return Model(
        id=model_id,
        owned_by="kitchen-ai"
    ) 