"""Custom exception hierarchy for the application."""


class AppError(Exception):
    """Base application error."""

    def __init__(self, message: str = "An application error occurred") -> None:
        self.message = message
        super().__init__(self.message)


class FileNotFoundError(AppError):
    """Raised when a requested file does not exist."""

    def __init__(self, message: str = "File not found") -> None:
        super().__init__(message)


class FileValidationError(AppError):
    """Raised when a file fails validation (type, size, etc.)."""

    def __init__(self, message: str = "File validation failed") -> None:
        super().__init__(message)


class DocumentNotFoundError(AppError):
    """Raised when a document record cannot be located."""

    def __init__(self, message: str = "Document not found") -> None:
        super().__init__(message)


class ProcessingError(AppError):
    """Raised when document processing fails."""

    def __init__(self, message: str = "Processing failed") -> None:
        super().__init__(message)


class VectorStoreError(AppError):
    """Raised when the vector store is unavailable or empty."""

    def __init__(self, message: str = "Vector store error") -> None:
        super().__init__(message)


class QueryError(AppError):
    """Raised when a RAG query fails."""

    def __init__(self, message: str = "Query failed") -> None:
        super().__init__(message)
