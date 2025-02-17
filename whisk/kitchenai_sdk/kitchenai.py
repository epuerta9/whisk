from .taxonomy.chat import ChatTask
from .taxonomy.storage import StorageTask
from .taxonomy.embeddings import EmbedTask
from .taxonomy.agent import AgentTask
from .base import DependencyManager


class KitchenAIApp:
    def __init__(self, namespace: str = "default", version: str = "0.0.1"):
        self.namespace = namespace
        self.version = version
        self.client_type = 'bento_box'
        self.client_description = 'Bento box'
        self.manager = DependencyManager()
        self.chat = ChatTask(namespace, self.manager)
        self.storage = StorageTask(namespace, self.manager)
        self.embeddings = EmbedTask(namespace, self.manager)
        self.agent = AgentTask(namespace, self.manager)
        self._mounted_apps = {}

    def mount_app(self, prefix: str, app: 'KitchenAIApp'):
        """Mount a sub-app and merge its handlers with prefixed labels"""
        # Merge dependencies
        for dep_type, dep in app.manager._dependencies.items():
            if dep_type not in self.manager._dependencies:
                self.manager.register_dependency(dep_type, dep)
        
        # Store mounted app
        self._mounted_apps[prefix] = app
        
        # Merge handlers with prefixed labels
        chat_tasks = app.chat.list_tasks()
        if isinstance(chat_tasks, list):
            chat_tasks = {task.__name__: task for task in chat_tasks}
        for label, handler in chat_tasks.items():
            prefixed_label = f"{prefix}.{label}"
            self.chat.register_task(prefixed_label, handler)
            
        storage_tasks = app.storage.list_tasks()
        if isinstance(storage_tasks, list):
            storage_tasks = {task.__name__: task for task in storage_tasks}
        for label, handler in storage_tasks.items():
            prefixed_label = f"{prefix}.{label}"
            self.storage.register_task(prefixed_label, handler)
            
        embed_tasks = app.embeddings.list_tasks()
        if isinstance(embed_tasks, list):
            embed_tasks = {task.__name__: task for task in embed_tasks}
        for label, handler in embed_tasks.items():
            prefixed_label = f"{prefix}.{label}"
            self.embeddings.register_task(prefixed_label, handler)

    def register_dependency(self, dep_type, dep):
        """Register dependency and propagate to mounted apps"""
        self.manager.register_dependency(dep_type, dep)
        for app in self._mounted_apps.values():
            if dep_type not in app.manager._dependencies:
                app.manager.register_dependency(dep_type, dep)

    def set_manager(self, manager):
        """Update the manager for the app and all tasks."""
        self.manager = manager
        self.chat._manager = manager
        self.storage._manager = manager
        self.embeddings._manager = manager
        self.agent._manager = manager

    def to_dict(self) -> dict:
        """Convert app configuration to dictionary format"""
        return {
            "namespace": self.namespace,
            "chat_handlers": list(self.chat.list_tasks()),
            "storage_handlers": list(self.storage.list_tasks()),
            "embed_handlers": list(self.embeddings.list_tasks()),
            "agent_handlers": list(self.agent.list_tasks())
        }
