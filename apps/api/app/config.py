from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+psycopg://claimguard:claimguard@localhost:5433/claimguard"
    )
    api_key: str = "dev-local-key"
    port: int = 4001
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:14b-instruct-q4_K_M"
    ollama_embed_model: str = "nomic-embed-text"


settings = Settings()
