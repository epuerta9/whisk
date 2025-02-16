from ..base import KitchenAITask, DependencyManager
import functools
from ..schema import DependencyType

class ChatTask(KitchenAITask):
    def __init__(self, namespace: str, manager: DependencyManager):
        super().__init__(namespace, manager)

    def handler(self, label: str, *dependencies: DependencyType):
        """Decorator for registering chat completion handlers with dependencies."""
        def decorator(func):
            @functools.wraps(func)
            @self.with_dependencies(*dependencies)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
            return self.register_task(label, wrapper)
        return decorator

    def with_dependencies(self, *dependencies: DependencyType):
        """Decorator to inject dependencies into handler functions"""
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # Inject requested dependencies
                for dep in dependencies:
                    if self._manager and self._manager.has_dependency(dep):
                        kwargs[dep] = self._manager.get_dependency(dep)
                return await func(*args, **kwargs)
            return wrapper
        return decorator 