
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Image Relevance and Auto-Tagging"
    app_env: str = "development"
    database_url: str = "sqlite:///./image_matching_test.db"

    upload_dir: str = "data/uploads"
    max_upload_size_mb: int = 10

    metadata_provider: str = "mock"
    embedding_provider: str = "gemini"
    matching_threshold: float = 0.35

    embedding_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"

    gemini_api_key: str = ""
    gemini_vision_model: str = "gemini-3.8-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_embedding_dimensions: int = 768

    api_budget_usd: float = 5.0

    gemini_vision_input_cost_per_million_tokens: float = 0.0
    gemini_vision_output_cost_per_million_tokens: float = 0.0
    gemini_embedding_cost_per_million_characters: float = 0.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
