from fastapi import APIRouter
from .chat import router as chat_router
from .models import router as models_router
from .files import router as files_router

router = APIRouter()
router.include_router(chat_router)
router.include_router(models_router)
router.include_router(files_router) 