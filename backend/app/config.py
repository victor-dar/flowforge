from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./flowforge.db"
    secret_key: str = "change-this-secret-before-deploying"
    access_token_minutes: int = 60 * 24
    cors_origins: str = "http://localhost:5173"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    max_message_length: int = 4000
    max_document_bytes: int = 5 * 1024 * 1024


settings = Settings()
