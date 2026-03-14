"""Centralized application constants."""

# Vector store
DEFAULT_CHROMA_PERSIST_DIR: str = "./chroma_db"
DEFAULT_DOCSTORE_PATH: str = "./docstore.json"
COLLECTION_NAME: str = "document_summaries"

# Retrieval
DEFAULT_SEARCH_K: int = 5
DEFAULT_SEARCH_TYPE: str = "similarity"
DEFAULT_ID_KEY: str = "doc_id"

# Partitioning
DEFAULT_PARTITION_STRATEGY: str = "hi_res"
DEFAULT_MAX_CHARACTERS: int = 10000
DEFAULT_COMBINE_UNDER_N_CHARS: int = 2000
DEFAULT_NEW_AFTER_N_CHARS: int = 6000
DEFAULT_IMAGE_TYPES: list[str] = ["Image"]

# LLM
VISION_MODEL: str = "llava"
SUMMARIZATION_TEMPERATURE: float = 0.5
VISION_TEMPERATURE: float = 0.7

# Ingestion
DEFAULT_MAX_CONCURRENCY: int = 3

# File I/O
FILE_WRITE_CHUNK_SIZE: int = 1024 * 1024  # 1 MB
