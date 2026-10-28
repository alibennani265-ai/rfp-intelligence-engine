from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RFP-Intelligence-Engine"
    env: str = "development"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    embedding_model_name: str = "BAAI/bge-m3"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()