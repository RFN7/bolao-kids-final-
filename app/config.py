from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    JWT_SECRET: str
    ENVIRONMENT: str = "local"
    FOOTBALL_API_KEY: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
