from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    JWT_SECRET: str
    ENVIRONMENT: str = "local"
    FOOTBALL_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    model_config = {"env_file": ".env"}

    @model_validator(mode="after")
    def _require_anthropic_key_in_production(self) -> "Settings":
        if self.ENVIRONMENT == "production" and not self.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY é obrigatória em produção")
        return self


settings = Settings()
