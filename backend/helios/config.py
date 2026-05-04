from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./helios.db"
    gemini_api_key: str = ""
    gemini_audit_model: str = "gemini-2.5-pro"
    gemini_fix_model: str = "gemini-2.5-pro"
    gemini_route_model: str = "gemini-2.5-flash"

    sandbox_timeout_s: int = 5
    sandbox_mem_mb: int = 512
    sandbox_stdout_cap_bytes: int = 1_000_000
    max_file_lines: int = 4000
    test_case_count: int = 12

    # Live audit
    gemini_live_model: str = "gemini-2.5-flash"
    live_max_file_lines: int = 1500
    live_rate_capacity: int = 30          # tokens in bucket
    live_rate_refill_per_s: float = 1.0   # tokens per second
    live_cache_max_tokens: int = 256      # max distinct session tokens cached
    live_cache_ttl_s: int = 1800          # idle session expiry


settings = Settings()
