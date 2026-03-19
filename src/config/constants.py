"""Centralized application constants."""

# Vector store
DEFAULT_CHROMA_PERSIST_DIR: str = "./chroma_db"
DEFAULT_DOCSTORE_PATH: str = "./docstore.json"
COLLECTION_NAME: str = "document_summaries"

# Retrieval
DEFAULT_SEARCH_K: int = 5
DEFAULT_FETCH_K: int = 20
DEFAULT_SEARCH_TYPE: str = "mmr"
DEFAULT_ID_KEY: str = "doc_id"

# Context management
MAX_CONTEXT_TOKENS: int = 3000
MAX_HISTORY_EXCHANGES: int = 4

# Partitioning
DEFAULT_PARTITION_STRATEGY: str = "hi_res"
DEFAULT_MAX_CHARACTERS: int = 3000
DEFAULT_COMBINE_UNDER_N_CHARS: int = 500
DEFAULT_NEW_AFTER_N_CHARS: int = 2000
DEFAULT_IMAGE_TYPES: list[str] = ["Image"]

# LLM
VISION_MODEL: str = "llava"
SUMMARIZATION_TEMPERATURE: float = 0.5
QA_TEMPERATURE: float = 0.7
VISION_TEMPERATURE: float = 0.7
LLM_MAX_RETRIES: int = 3

# Ingestion
DEFAULT_MAX_CONCURRENCY: int = 3

# File I/O
FILE_WRITE_CHUNK_SIZE: int = 1024 * 1024  # 1 MB

# Input validation
MAX_QUESTION_LENGTH: int = 2000
