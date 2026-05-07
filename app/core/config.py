from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./analytics.db"
    CACHE_TTL_SECONDS: int = 60
    MAX_BATCH_SIZE: int = 1000
    APP_TITLE: str = "Feature Analytics API"
    APP_VERSION: str = "1.0.0"

    class Config:
        env_file = ".env"


settings = Settings()
