from typing import Optional
from .kitchenai_sdk.kitchenai import KitchenAIApp

# Global app instance
_app: Optional[KitchenAIApp] = None

def get_kitchen_app() -> KitchenAIApp:
    """Get KitchenAI app instance"""
    if _app is None:
        raise RuntimeError("KitchenAI app not initialized")
    return _app

def set_kitchen_app(app: KitchenAIApp):
    """Set the KitchenAI app instance"""
    global _app
    _app = app 