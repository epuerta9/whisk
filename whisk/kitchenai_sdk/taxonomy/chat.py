from typing import Dict, Any, Callable, Union
from functools import wraps
from ..base import TaskRegistry
from ..schema import ChatInput, ChatResponse, ChatCompletionResponse, DependencyType

class ChatTask(TaskRegistry):
    """Chat task registry"""
    
    def __init__(self, namespace: str, manager=None):
        super().__init__(namespace, manager)
        self.task_type = "chat"

    def handler(self, name: str, *dependencies: Union[DependencyType, str]):
        """Decorator for simplified chat handlers"""
        def decorator(func: Callable[[ChatInput], ChatResponse]):
            @wraps(func)
            async def wrapper(request: Any):
                # Inject requested dependencies
                kwargs = {}
                if self._manager:
                    for dep in dependencies:
                        dep_key = dep.value if hasattr(dep, 'value') else dep
                        if self._manager.has_dependency(dep):
                            kwargs[dep_key] = self._manager.get_dependency(dep)
                        else:
                            raise KeyError(f"Required dependency {dep} not found")

                # Convert OpenAI request to simplified input
                chat_input = ChatInput.from_request(request)
                
                # Call handler with simplified input and dependencies
                response = await func(chat_input, **kwargs)
                
                # If response is already in OpenAI format, return it directly
                if isinstance(response, ChatCompletionResponse):
                    return response
                
                # Convert simplified response to OpenAI format
                openai_response = ChatCompletionResponse(
                    model=request.model,
                    choices=[{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": response.content
                        },
                        "finish_reason": "stop"
                    }]
                )

                # Include sources in response metadata if available and requested
                if response.sources and (
                    request.metadata and request.metadata.get("include_sources", False)
                ):
                    openai_response.metadata = {
                        "sources": [source.dict() for source in response.sources]
                    }
                
                return openai_response
            
            # Register the wrapped handler
            return self.register_task(name, wrapper)
        return decorator

    def get_task(self, name: str) -> Callable:
        """Get a chat task by name"""
        return self._tasks.get(name)

    def list_tasks(self) -> Dict[str, Callable]:
        """List all registered chat tasks"""
        return self._tasks 