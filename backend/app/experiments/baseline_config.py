"""
Phase 6: Immutable Baseline Strategy Configuration & Versioning
Guarantees baseline strategy parameters remain strictly frozen during forensic experiments.
"""
from typing import Any, Dict
from pydantic import BaseModel, Field

BASELINE_VERSION = "phase6-baseline-v1"


class FrozenBaselineConfig(BaseModel):
    """
    Immutable Baseline Configuration for Phase 6 Forensics and Experiments.
    Represents the exact operational baseline from Phase 5B.
    """
    version: str = Field(default=BASELINE_VERSION, frozen=True)
    symbol: str = Field(default="XAUUSD", frozen=True)
    timeframe_primary: str = Field(default="5m", frozen=True)
    timeframe_trigger: str = Field(default="1m", frozen=True)
    signal_threshold: int = Field(default=7, frozen=True)
    sl_atr_multiplier: float = Field(default=1.0, frozen=True)
    tp1_atr_multiplier: float = Field(default=1.0, frozen=True)
    tp2_atr_multiplier: float = Field(default=2.0, frozen=True)
    max_holding_minutes: int = Field(default=60, frozen=True)
    assumed_spread: float = Field(default=0.30, frozen=True)
    execution_mode: str = Field(default="fixed_spread", frozen=True)
    same_candle_policy: str = Field(default="stop_first", frozen=True)
    max_concurrent_trades: int = Field(default=1, frozen=True)
    initial_capital: float = Field(default=10000.0, frozen=True)
    risk_per_trade_usd: float = Field(default=100.0, frozen=True)
    enable_long: bool = Field(default=True, frozen=True)
    enable_short: bool = Field(default=True, frozen=True)

    model_config = {
        "frozen": True,
        "extra": "forbid"
    }


def get_frozen_baseline_config() -> FrozenBaselineConfig:
    """Return an immutable instance of the frozen Phase 6 baseline configuration."""
    return FrozenBaselineConfig()
