import pytest

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    test_api_key: str


settings = Settings()


@pytest.fixture
def api_key():
    yield settings.test_api_key
