from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+psycopg://claimguard:claimguard@localhost:5433/claimguard"
    )
    api_key: str = "dev-local-key"
    # "key:actor:role,..." — role reviewer|admin. Reviews are refused unless the caller holds one of these keys.
    reviewer_keys: str = ""
    cors_origins: str = "http://localhost:3000"  # comma-separated; never "*" with credentials
    port: int = 4001
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:14b-instruct-q4_K_M"
    ollama_embed_model: str = "nomic-embed-text"
    rules_dir: str = ""
    audit_enabled: bool = True
    audit_log_path: str = ""
    rule_engine_max_batch: int = 1000

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def resolved_rules_dir(self) -> Path:
        if self.rules_dir.strip():
            return Path(self.rules_dir)
        return _REPO_ROOT / "data" / "payer-rules"

    def resolved_audit_log(self) -> Path:
        if self.audit_log_path.strip():
            return Path(self.audit_log_path)
        return _REPO_ROOT / "outputs" / "audit.jsonl"


settings = Settings()
