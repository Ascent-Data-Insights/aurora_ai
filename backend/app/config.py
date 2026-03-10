from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    cartesia_api_key: str = ""
    model_heavy: str = "claude-sonnet-4-6"
    model_light: str = "claude-haiku-4-5-20251001"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def api_key(self) -> str:
        return self.anthropic_api_key


settings = Settings()  # type: ignore[call-arg]
