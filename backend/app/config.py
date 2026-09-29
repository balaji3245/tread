from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Server settings
    backend_host: str = Field(default="127.0.0.1", alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001"],
        alias="CORS_ORIGINS"
    )

    # Market Data settings
    mt5_symbol: str = Field(default="XAUUSD", alias="MT5_SYMBOL")
    historical_candle_count: int = Field(default=300, alias="HISTORICAL_CANDLE_COUNT")
    tick_poll_interval_ms: int = Field(default=100, alias="TICK_POLL_INTERVAL_MS")
    stale_data_threshold_seconds: float = Field(default=5.0, alias="STALE_DATA_THRESHOLD_SECONDS")

    # MT5 configuration
    mt5_path: str = Field(default="", alias="MT5_PATH")
    mt5_bridge_url: str = Field(default="http://127.0.0.1:18812", alias="MT5_BRIDGE_URL")
    mt5_mock_fallback: bool = Field(
        default=True,
        alias="MT5_MOCK_FALLBACK",
        description="Allow realistic simulated gold ticks if MT5 is not available/running on local OS"
    )


settings = Settings()
