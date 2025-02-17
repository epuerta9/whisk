import logging
from typing import Dict, Any, List, Optional
from whisk.kitchenai_sdk.kitchenai import KitchenAIApp
from whisk.kitchenai_sdk.http_schema import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatResponseMessage
)
import time
import json

logger = logging.getLogger(__name__)

class CommandMiddleware:
    """Middleware for handling chat commands"""
    
    def __init__(self, app: KitchenAIApp):
        self.app = app
        self.commands = {
            "/capabilities": self.show_capabilities,
            "/show": self.show_all,
            "/chat": self.show_chat_handlers,
            "/file": self.show_file_handlers,
            "/eval": self.show_eval_handlers,
            "/help": self.show_help
        }
        logger.info(f"Command middleware initialized with commands: {list(self.commands.keys())}")

    async def handle_command(self, request: ChatCompletionRequest) -> Optional[ChatCompletionResponse]:
        """Check if message is a command and handle it"""
        if not request.messages or not request.messages[-1].content:
            logger.debug("No messages or empty content")
            return None
            
        command = request.messages[-1].content.strip()
        logger.info(f"Checking command: {command}")
        
        if not command.startswith("/"):
            logger.debug("Not a command message")
            return None

        # Get command handler
        cmd = command.split()[0]  # Get first word as command
        logger.info(f"Looking for handler for command: {cmd}")
        
        handler = self.commands.get(cmd)
        if not handler:
            logger.warning(f"Unknown command: {cmd}")
            return self.create_response(
                f"Unknown command '{command}'. Use /help to see available commands."
            )

        logger.info(f"Executing command: {cmd}")
        return await handler(command)

    def create_response(self, content: str) -> Dict[str, Any]:
        """Create a chat completion response with given content"""
        logger.info(f"Creating command response with content: {content}")
        
        timestamp = int(time.time())
        response = {
            "id": f"chatcmpl-{timestamp}",
            "object": "chat.completion",
            "created": timestamp,
            "model": "gpt-3.5-turbo",
            "system_fingerprint": "fp_44709d6fcb",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "logprobs": None,
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": len(content.split()),
                "total_tokens": len(content.split())
            }
        }
        
        logger.info(f"Formatted response: {json.dumps(response, indent=2)}")
        return response

    async def show_capabilities(self, _: str) -> ChatCompletionResponse:
        """Show all app capabilities"""
        app_dict = self.app.to_dict()
        capabilities = []
        
        if app_dict.get("chat_handlers"):
            capabilities.append("\nChat Handlers:")
            for name in app_dict["chat_handlers"]:
                capabilities.append(f"  • {name}")
                
        if app_dict.get("storage_handlers"):
            capabilities.append("\nStorage Handlers:")
            for name in app_dict["storage_handlers"]:
                capabilities.append(f"  • {name}")
                
        if app_dict.get("embed_handlers"):
            capabilities.append("\nEmbedding Handlers:")
            for name in app_dict["embed_handlers"]:
                capabilities.append(f"  • {name}")

        return self.create_response("\n".join(capabilities))

    async def show_all(self, _: str) -> ChatCompletionResponse:
        """Show detailed info about all handlers"""
        app_dict = self.app.to_dict()
        details = ["App Details:", f"Namespace: {self.app.namespace}"]
        
        # Show dependencies
        if hasattr(self.app.manager, '_dependencies'):
            deps = self.app.manager._dependencies
            if deps:
                details.append("\nDependencies:")
                for dep_type, dep in deps.items():
                    details.append(f"  • {dep_type}: {type(dep).__name__}")

        # Show handlers with more details
        for category in ["chat_handlers", "storage_handlers", "embed_handlers"]:
            if handlers := app_dict.get(category):
                details.append(f"\n{category.replace('_', ' ').title()}:")
                # Handle both list and dict cases
                if isinstance(handlers, dict):
                    for name, info in handlers.items():
                        details.append(f"  • {name}")
                        if hasattr(info, "dependencies"):
                            details.append(f"    Dependencies: {', '.join(info.dependencies)}")
                else:  # It's a list
                    for name in handlers:
                        details.append(f"  • {name}")

        return self.create_response("\n".join(details))

    async def show_chat_handlers(self, _: str) -> ChatCompletionResponse:
        """Show chat handlers"""
        handlers = self.app.chat.list_tasks()
        content = ["Chat Handlers:"]
        for name in handlers:
            content.append(f"  • {name}")
        return self.create_response("\n".join(content))

    async def show_file_handlers(self, _: str) -> ChatCompletionResponse:
        """Show file/storage handlers"""
        handlers = self.app.storage.list_tasks()
        content = ["File/Storage Handlers:"]
        for name in handlers:
            content.append(f"  • {name}")
        return self.create_response("\n".join(content))

    async def show_eval_handlers(self, _: str) -> ChatCompletionResponse:
        """Show evaluation handlers"""
        # TODO: Implement eval handlers
        return self.create_response("Evaluation handlers not implemented yet")

    async def show_help(self, _: str) -> ChatCompletionResponse:
        """Show help for available commands"""
        help_text = """Available Commands:
/capabilities - Show all app capabilities and handlers
/show        - Show detailed information about the app
/chat        - List chat handlers
/file        - List file/storage handlers
/eval        - List evaluation handlers
/help        - Show this help message"""
        
        logger.info(f"Sending help text: {help_text}")
        return self.create_response(help_text) 