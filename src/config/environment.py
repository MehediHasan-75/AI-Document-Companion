from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    #owerwriting model_config of BaseSettings
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "AI DOCUMENT COMPANION"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql://rag_user:rag_password@localhost:5432/rag_db"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40

    # LLM
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "deepseek-r1:8b"

    # Embeddings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Processing
    MAX_UPLOAD_SIZE: int = 50
    UPLOAD_DIR: str = "./uploads"
    UPLOAD_DIRECTORY: str | None = None
    MAX_FILE_SIZE: int | None = None

    # Auth tokens
    HUGGING_FACE_HUB_TOKEN: str | None = None

    # CORS
    CORS_ALLOWED_ORIGINS: list[str] = ["*"]

    # JWT Authentication
    SECRET_KEY: str = "change-this-to-a-long-random-secret-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    @property
    def embedding_model_name(self) -> str:
        """Short model name extracted from the full model path."""
        return self.EMBEDDING_MODEL