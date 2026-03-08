"""
Services Package.

Business logic services that implement core functionality for the
document processing and RAG pipeline. Services are responsible for:
- Document ingestion and processing
- Vector storage and retrieval
- LLM integration and summarization
- File management

Available Services:
    - file_service: File upload, storage, and deletion
    - process_service: Document processing orchestration
    - query_service: RAG query handling
    - ingestion_service: Document ingestion pipeline
    - vector_service: Vector store management
    - retrival_service: Multi-vector retrieval
    - llm_service: LLM chain construction
    - chunk_service: Document chunk processing
    - embedding_service: Embedding model factory
    - unstructured_service: PDF partitioning

Integration Points:
    - REDIS_INTEGRATION: Caching and distributed state
    - WEBSOCKET_INTEGRATION: Real-time event emission
    - MQ_INTEGRATION: Async job processing

Example:
    >>> from src.services import file_service, query_service
    >>> doc_id = file_service.save_upload(file)
    >>> answer = query_service.ask_question("What is AI?")
"""

from src.services.file_service import file_service, FileService
from src.services.process_service import process_service, ProcessService
from src.services.query_service import query_service, QueryService

# Import key functions from other services
from src.services.ingestion_service import ingest_document_pipeline
from src.services.vector_service import get_vectorstore, get_docstore, SimpleDocStore
from src.services.retrival_service import (
    get_multi_vector_retriever,
    add_documents_to_retriever,
    retrieve_with_sources,
)
from src.services.llm_service import (
    get_text_table_summarizer,
    get_image_summarizer,
    get_rag_chain,
)
from src.services.chunk_service import separate_elements, get_images_base64
from src.services.embedding_service import get_openai_embeddings
from src.services.unstructured_service import partition_document


__all__ = [
    # Singleton instances
    "file_service",
    "process_service",
    "query_service",
    # Classes
    "FileService",
    "ProcessService",
    "QueryService",
    "SimpleDocStore",
    # Ingestion
    "ingest_document_pipeline",
    # Vector operations
    "get_vectorstore",
    "get_docstore",
    "get_multi_vector_retriever",
    "add_documents_to_retriever",
    "retrieve_with_sources",
    # LLM operations
    "get_text_table_summarizer",
    "get_image_summarizer",
    "get_rag_chain",
    # Chunk processing
    "separate_elements",
    "get_images_base64",
    # Embeddings
    "get_openai_embeddings",
    # Document partitioning
    "partition_document",
]
