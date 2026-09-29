from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class HistoricalCandle(BaseModel):
    time: int
    open: float
    high: float
    low: float
    close: float
    tick_volume: Optional[int] = None
    spread: Optional[float] = None
    real_volume: Optional[int] = None


class BacktestConfig(BaseModel):
    symbol: str = "XAUUSD"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    timeframe_primary: str = "5m"
    timeframe_trigger: str = "1m"
    initial_capital: float = Field(default=10000.0, gt=0, description="Starting capital")
    risk_per_trade_usd: float = Field(default=100.0, gt=0, description="Virtual dollar risk per trade (1R)")
    signal_threshold: int = Field(default=7, ge=1, le=10, description="Signal score threshold (1-10)")
    sl_atr_multiplier: float = Field(default=1.0, gt=0, description="Stop-Loss ATR multiplier")
    tp1_atr_multiplier: float = Field(default=1.0, gt=0, description="TP1 ATR multiplier")
    tp2_atr_multiplier: float = Field(default=2.0, gt=0, description="TP2 ATR multiplier")
    max_holding_minutes: int = Field(default=60, ge=5, le=1440, description="Max trade holding minutes before expiry")
    assumed_spread: float = Field(default=0.30, ge=0.0, description="Spread assumption in USD")
    execution_mode: Literal["fixed_spread", "historical_spread"] = "fixed_spread"
    same_candle_policy: Literal["stop_first", "tp_first"] = "stop_first"
    max_concurrent_trades: int = Field(default=1, ge=1, le=5)
    enable_long: bool = True
    enable_short: bool = True
    # Phase 6B Exit & Invalidation Extensions
    breakeven_trigger_r: Optional[float] = Field(default=None, description="Trigger in R-multiples to move stop loss to entry price")
    trailing_stop_atr: Optional[float] = Field(default=None, description="Trailing stop distance in ATR multiples")
    trailing_trigger_r: Optional[float] = Field(default=None, description="Trigger in R-multiples to activate trailing stop")
    time_invalidation_minutes: Optional[int] = Field(default=None, description="Holding time in minutes to check for minimum favorable excursion")
    time_invalidation_min_mfe_r: Optional[float] = Field(default=None, description="Minimum MFE in R required by time invalidation limit")


class BacktestTrade(BaseModel):
    id: str
    symbol: str
    direction: Literal["LONG", "SHORT"]
    signal_time: int
    signal_time_iso: str
    entry_time: int
    entry_time_iso: str
    exit_time: int
    exit_time_iso: str
    signal_strength: int
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    exit_price: float
    result: Literal["TP1", "TP2", "STOP_LOSS", "EXPIRED"]
    pnl: float
    r_multiple: float
    holding_minutes: float
    exit_reason: str
    entry_reason: Optional[str] = None
    market_regime: Optional[str] = None
    session: Optional[str] = None
    # Excursions
    mae_r: Optional[float] = None
    mfe_r: Optional[float] = None
    mae_price: Optional[float] = None
    mfe_price: Optional[float] = None


class EquityPoint(BaseModel):
    time: int
    time_iso: str
    equity: float
    drawdown: float
    drawdown_pct: float


class StrengthStat(BaseModel):
    strength: int
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_r: float
    average_r: float
    profit_factor: float


class DirectionStat(BaseModel):
    direction: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_r: float
    average_r: float
    profit_factor: float
    max_drawdown: float


class SessionStat(BaseModel):
    session: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_r: float
    average_r: float


class BacktestStatistics(BaseModel):
    total_signals: int = 0
    total_trades: int = 0
    long_trades: int = 0
    short_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    expired_trades: int = 0
    win_rate: float = 0.0
    total_r: float = 0.0
    average_r: float = 0.0
    median_r: float = 0.0
    profit_factor: float = 0.0
    average_win_r: float = 0.0
    average_loss_r: float = 0.0
    largest_win_r: float = 0.0
    largest_loss_r: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    average_holding_minutes: float = 0.0
    longest_holding_minutes: float = 0.0
    by_strength: List[StrengthStat] = Field(default_factory=list)
    by_direction: Dict[str, DirectionStat] = Field(default_factory=dict)
    by_session: List[SessionStat] = Field(default_factory=list)
    by_regime: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class BacktestResponse(BaseModel):
    symbol: str = "XAUUSD"
    period: Dict[str, str]
    configuration: Dict[str, Any]
    execution_metadata: Dict[str, Any]
    statistics: BacktestStatistics
    trades: List[BacktestTrade]
    equity_curve: List[EquityPoint]
