from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки читаются из переменных окружения и файла .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/taskdb"
    test_database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/taskdb_test"
    )


settings = Settings()
