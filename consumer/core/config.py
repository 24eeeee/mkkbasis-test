from os import getenv

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = getenv('DATABASE_URL')
    rabbitmq_url: str = getenv('RABBITMQ_URL')
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

settings = Settings()
