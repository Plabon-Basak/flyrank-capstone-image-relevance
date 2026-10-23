
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Image Relevance and Auto-Tagging"
    app_env: str = "development"
    database_url: str = "sqlite:///./image_matching_test.db"
    upload_dir: str = "data/uploads"
    max_upload_size_mb: int = 10
    metadata_provider: str = "mock"
    embedding_provider: str = "mock"
    matching_threshold: float = 0.35
    embedding_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
