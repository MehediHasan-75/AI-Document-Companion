"""Custom exception hierarchy for the application."""


class AppError(Exception):
    """Base application error. Subclasses declare their own status_code."""

    status_code: int = 500

    def __init__(self, message: str = "An application error occurred") -> None:
        self.message = message
        super().__init__(self.message)


class FileNotFoundError(AppError):
    status_code = 404

    def __init__(self, message: str = "File not found") -> None:
        super().__init__(message)


class DocumentNotFoundError(AppError):
    status_code = 404

    def __init__(self, message: str = "Document not found") -> None:
        super().__init__(message)


class FileValidationError(AppError):
    status_code = 400

    def __init__(self, message: str = "File validation failed") -> None:
        super().__init__(message)


class AuthenticationError(AppError):
    status_code = 401

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message)


class ConflictError(AppError):
    status_code = 409

    def __init__(self, message: str = "Resource already exists") -> None:
        super().__init__(message)


class VectorStoreError(AppError):
    status_code = 503

    def __init__(self, message: str = "Vector store error") -> None:
        super().__init__(message)


class ProcessingError(AppError):
    status_code = 422

    def __init__(self, message: str = "Processing failed") -> None:
        super().__init__(message)


class QueryError(AppError):
    status_code = 422

    def __init__(self, message: str = "Query failed") -> None:
        super().__init__(message)
