from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./flowforge.db"
    secret_key: str = "change-this-secret-before-deploying"
    access_token_minutes: int = 60 * 24
    cors_origins: str = "http://localhost:5173"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    max_message_length: int = 4000
    max_document_bytes: int = 5 * 1024 * 1024
    max_document_characters: int = Field(default=500_000, gt=0)
    auth_rate_limit_per_minute: int = Field(default=10, gt=0)
    public_chat_rate_limit_per_minute: int = Field(default=20, gt=0)
    public_chat_daily_limit_per_bot: int = Field(default=500, gt=0)
    ai_max_output_tokens: int = Field(default=600, gt=0, le=4000)

    def validate_deployment(self) -> None:
        if self.app_env.lower() != "production":
            return
        if (
            len(self.secret_key) < 32
            or self.secret_key
            in {
                "change-this-secret-before-deploying",
                "troque-por-uma-chave-secreta-longa-e-unica",
            }
        ):
            raise RuntimeError("Configure uma SECRET_KEY forte e única antes de rodar em produção.")
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        if not origins or any("*" in origin for origin in origins):
            raise RuntimeError("Configure CORS_ORIGINS explícitas em produção.")


settings = Settings()
