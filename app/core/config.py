from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str = Field(min_length=32)
    jwt_expire_minutes: int = Field(default=120, ge=1, le=1440)
    jwt_issuer: str = "eventease-api"
    jwt_audience: str = "eventease-client"
    enable_demo_login: bool = False
    seed_demo_data: bool = False
    cors_origins: list[str] = Field(default_factory=list)
    db_pool_size: int = Field(default=3, ge=1, le=20)
    db_max_overflow: int = Field(default=2, ge=0, le=20)


@lru_cache
def get_settings() -> Settings:
    return Settings()
