from collections.abc import Callable
import logging
from functools import wraps
import asyncio
from .schema import DependencyType
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)

class DependencyManager:
    """Manages dependencies for KitchenAI tasks"""
    
    def __init__(self):
        self._dependencies: Dict[DependencyType, Any] = {}
        
    def register_dependency(self, dep_type: DependencyType, dep: Any):
        """Register a dependency"""
        self._dependencies[dep_type] = dep
        
    def get_dependency(self, dep_type: DependencyType) -> Any:
        """Get a registered dependency"""
        if dep_type not in self._dependencies:
            raise KeyError(f"Dependency {dep_type} not registered")
        return self._dependencies[dep_type]
    
    def has_dependency(self, dep_type: DependencyType) -> bool:
        """Check if a dependency is registered"""
        return dep_type in self._dependencies

class TaskRegistry:
    """Base class for task registries"""
    def __init__(self, namespace: str, manager: Optional[DependencyManager] = None):
        self.namespace = namespace
        self._manager = manager
        self._tasks: Dict[str, Callable] = {}
        self.task_type = "base"

    def handler(self, name: str, *dependencies: Union[DependencyType, str]):
        """Decorator for registering task handlers with dependencies"""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Inject requested dependencies
                if self._manager:
                    for dep in dependencies:
                        dep_key = dep.value if hasattr(dep, 'value') else dep
                        if self._manager.has_dependency(dep):
                            kwargs[dep_key] = self._manager.get_dependency(dep)
                        else:
                            raise KeyError(f"Required dependency {dep} not found")
                return await func(*args, **kwargs)
            return self.register_task(name, wrapper)
        return decorator

    def register_task(self, name: str, task: Callable) -> Callable:
        """Register a task with the given name"""
        self._tasks[name] = task
        return task

    def get_task(self, name: str) -> Optional[Callable]:
        """Get a task by name"""
        return self._tasks.get(name)

    def list_tasks(self) -> Dict[str, Callable]:
        """List all registered tasks"""
        return self._tasks

class KitchenAITask:
    def __init__(self, namespace: str, manager=None):
        self.namespace = namespace
        self._manager = manager
        self._tasks = {}
        self._hooks = {}

    def with_dependencies(self, *dep_types: DependencyType | str) -> Callable:
        """Decorator to inject dependencies into task functions."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Inject requested dependencies into kwargs
                if self._manager:
                    for dep_type in dep_types:
                        if self._manager.has_dependency(dep_type):
                            # Use value for enum types, or key directly for strings
                            key = dep_type.value if isinstance(dep_type, DependencyType) else dep_type
                            kwargs[key] = self._manager.get_dependency(dep_type)
                return await func(*args, **kwargs)
            return wrapper
        return decorator

    def register_task(self, label: str, task):
        """Register a task with a label"""
        self._tasks[label] = task
        return task

    def get_task(self, label: str):
        """Get a task by label"""
        return self._tasks.get(label)

    def list_tasks(self):
        """List all registered tasks"""
        return self._tasks


class KitchenAITaskHookMixin:
    def register_hook(self, label: str, hook_type: str, func: Callable):
        """Register a hook function with the given label."""
        hook_key = f"{self.namespace}.{label}.{hook_type}"
        self._hooks[hook_key] = func
        return func

    def get_hook(self, label: str, hook_type: str) -> Callable | None:
        """Get a registered hook function by label."""
        hook_key = f"{self.namespace}.{label}.{hook_type}"
        return self._hooks.get(hook_key)

    def list_hooks(self) -> list:
        """List all registered hook labels."""
        return list(self._hooks.keys())