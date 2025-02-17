"""API module for Whisk"""

def get_routers():
    """Get all API routers"""
    from .chat import router as chat_router
    from .files import router as files_router
    from .models import router as models_router
    return [chat_router, files_router, models_router] 