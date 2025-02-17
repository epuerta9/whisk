from ..base import KitchenAITask, KitchenAITaskHookMixin
import functools
from ..schema import DependencyType, WhiskStorageResponseSchema
from typing import Dict, Any, Optional, Callable

class StorageTask(KitchenAITask, KitchenAITaskHookMixin):
    """
    This is a class for registering storage tasks.
    """
    def __init__(self, namespace: str, dependency_manager=None):
        super().__init__(namespace, dependency_manager)
        self.handlers: Dict[str, Callable] = {}
        self.delete_handlers: Dict[str, Callable] = {}

    def handler(self, name: str, *dependencies: DependencyType):
        """Register a storage handler"""
        def decorator(func):
            @functools.wraps(func)
            @self.with_dependencies(*dependencies)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
            self.handlers[name] = wrapper
            # Also register as a task for compatibility
            self.register_task(name, wrapper)
            return wrapper
        return decorator

    def get_handler(self, name: str) -> Optional[Callable]:
        """Get a registered handler"""
        return self.handlers.get(name)

    async def execute(self, name: str, data: Any) -> Any:
        """Execute a storage handler"""
        handler = self.get_handler(name)
        if not handler:
            raise ValueError(f"Handler {name} not found")
        
        # Execute handler and validate response
        response = await handler(data)
        
        # Validate response against schema
        if isinstance(response, dict):
            # Convert dict to schema
            try:
                response = WhiskStorageResponseSchema(**response)
            except Exception as e:
                raise ValueError(f"Invalid response format: {e}")
        elif not isinstance(response, WhiskStorageResponseSchema):
            raise ValueError("Response must be WhiskStorageResponseSchema")
            
        return response

    def on_delete(self, name: str, *dependencies: DependencyType):
        """Register a delete handler"""
        def decorator(func):
            @functools.wraps(func)
            @self.with_dependencies(*dependencies)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
            self.delete_handlers[name] = wrapper
            # Register as a hook
            self.register_hook(name, "on_delete", wrapper)
            return wrapper
        return decorator

    async def execute_delete(self, name: str, data: Any) -> None:
        """Execute a delete handler"""
        handler = self.delete_handlers.get(name)
        if handler:
            await handler(data)

    def on_store(self, label: str, *dependencies: DependencyType):
        """Decorator for registering storage hooks with dependencies."""
        def decorator(func):
            @functools.wraps(func)
            @self.with_dependencies(*dependencies)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return self.register_hook(label, "on_store", wrapper)
        return decorator
    
    def on_retrieve(self, label: str, *dependencies: DependencyType):
        """Decorator for registering retrieval hooks with dependencies."""
        def decorator(func):
            @functools.wraps(func)
            @self.with_dependencies(*dependencies)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return self.register_hook(label, "on_retrieve", wrapper)
        return decorator
