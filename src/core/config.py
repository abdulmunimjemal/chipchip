from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "ChipChip AI Marketing Agent"
    API_PREFIX: str = "/api/v1"

    # Google API Key
    GOOGLE_API_KEY: str

    # LLM Model
    LLM_MODEL_NAME: str = "models/gemini-2.5-flash-preview-04-17" 

    # ClickHouse Settings
    CLICKHOUSE_HOST: str = "localhost"
    CLICKHOUSE_PORT: int = 8123
    CLICKHOUSE_USERNAME: str = "default"
    CLICKHOUSE_PASSWORD: str = "sample"
    CLICKHOUSE_DATABASE: str = "chipchip_db"

    # Redis Settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0

    # PoC Table Names (as a list of strings)
    POC_TABLE_NAMES: list[str] = [
        "users_poc", "categories_poc", "products_poc",
        "orders_poc", "order_items_poc",
        "group_deals_poc", "groups_poc", "group_members_poc"
    ]
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

@lru_cache()  # cache for perf.
def get_settings() -> Settings:
    return Settings()

settings = get_settings()