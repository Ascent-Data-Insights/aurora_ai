from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_key: str
    model_heavy: str = "claude-sonnet-4-6"
    model_light: str = "claude-haiku-4-5-20251001"

    model_config = {"env_file": ".env"}


settings = Settings()  # type: ignore[call-arg]
