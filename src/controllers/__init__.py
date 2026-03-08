"""
Controllers Package.

HTTP-facing controllers that orchestrate request handling and delegate
to service layer for business logic. Controllers handle:
- Request/response transformation
- Error handling and HTTP status codes
- Coordination between services

Available Controllers:
    - FileController: File upload and deletion operations
    - ProcessController: Document processing orchestration
    - QueryController: RAG query operations
    - ChatController: Conversational chat (TODO)
    - DocumentController: Document management (TODO)
    - UploadController: Advanced uploads (TODO)

Integration Points:
    - WEBSOCKET_INTEGRATION: Real-time event handlers
    - MQ_INTEGRATION: Async job dispatching

Example:
    >>> from src.controllers import file_controller, query_controller
    >>> result = file_controller.upload_file(file)
    >>> answer = query_controller.ask("What is AI?")
"""

from src.controllers.file_controller import file_controller, FileController
from src.controllers.process_controller import process_controller, ProcessController
from src.controllers.query_controller import query_controller, QueryController
from src.controllers.chat_controller import chat_controller, ChatController
from src.controllers.document_controller import document_controller, DocumentController
from src.controllers.upload_controller import upload_controller, UploadController


__all__ = [
    # Singleton instances
    "file_controller",
    "process_controller",
    "query_controller",
    "chat_controller",
    "document_controller",
    "upload_controller",
    # Classes for testing/customization
    "FileController",
    "ProcessController",
    "QueryController",
    "ChatController",
    "DocumentController",
    "UploadController",
]