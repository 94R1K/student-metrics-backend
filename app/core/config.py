from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Базовые настройки приложения; переопределяются через переменные окружения."""

    secret_key: str = Field("CHANGE_ME", env="SECRET_KEY")
    algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_minutes: int = Field(60 * 24 * 7, env="REFRESH_TOKEN_EXPIRE_MINUTES")
    database_url: str = Field("sqlite:///./app.db", env="DATABASE_URL")
    refresh_cleanup_interval_seconds: int = Field(3600, env="REFRESH_CLEANUP_INTERVAL_SECONDS")
    clickhouse_url: str = Field("http://localhost:8123", env="CLICKHOUSE_URL")
    clickhouse_user: str = Field("default", env="CLICKHOUSE_USER")
    clickhouse_password: str = Field("", env="CLICKHOUSE_PASSWORD")
    clickhouse_database: str = Field("default", env="CLICKHOUSE_DATABASE")
    clickhouse_events_table: str = Field("events", env="CLICKHOUSE_EVENTS_TABLE")
    clickhouse_timeout_seconds: float = Field(2.0, env="CLICKHOUSE_TIMEOUT_SECONDS")

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
