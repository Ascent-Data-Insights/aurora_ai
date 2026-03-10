from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    cartesia_api_key: str = ""
    deepgram_api_key: str = ""
    model_heavy: str = "claude-sonnet-4-6"
    model_light: str = "claude-haiku-4-5-20251001"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()  # type: ignore[call-arg]
