from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Service
    service_name: str = "ai-agent-service"
    service_port: int = 8001
    environment: str = "development"
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+asyncpg://compass:compass_dev@localhost:5432/ai_agent_db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # LLM
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    primary_llm_model: str = "gpt-4"
    backup_llm_model: str = ""
    screening_llm_model: str = "gpt-4o-mini"
    llm_max_retries: int = 3
    llm_retry_backoff_seconds: int = 2
    llm_circuit_breaker_threshold: int = 5
    llm_circuit_breaker_timeout: int = 60

    # PHI
    phi_encryption_key: str = ""
    phi_mapping_ttl_hours: int = 24


settings = Settings()
