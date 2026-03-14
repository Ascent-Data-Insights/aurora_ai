from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    cartesia_api_key: str = ""
    deepgram_api_key: str = ""
    model_heavy: str = "claude-sonnet-4-6"
    model_light: str = "claude-haiku-4-5-20251001"
    database_url: str = "postgresql+asyncpg://aurora:aurora@localhost:5432/aurora"
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()  # type: ignore[call-arg]
