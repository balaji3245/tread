from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class PriceLevel(BaseModel):
    price: float
    type: Literal["support", "resistance"]
    strength: int = Field(ge=1, le=5, description="Strength score from 1 to 5 based on touches")


class SignalIndicators(BaseModel):
    ema9_1m: Optional[float] = None
    ema21_1m: Optional[float] = None
    ema50_1m: Optional[float] = None

    ema9_5m: Optional[float] = None
    ema21_5m: Optional[float] = None
    ema50_5m: Optional[float] = None

    rsi_1m: Optional[float] = None
    rsi_5m: Optional[float] = None

    macd_1m: Optional[float] = None
    macdSignal_1m: Optional[float] = None
    macdHist_1m: Optional[float] = None

    atr_1m: Optional[float] = None
    atr_5m: Optional[float] = None

    vwap_1m: Optional[float] = None


class MarketSignal(BaseModel):
    symbol: str = "XAUUSD"
    type: Literal["LONG_SETUP", "SHORT_SETUP", "WAIT"] = "WAIT"
    timeframe: str = "1m+5m"
    generatedAt: int
    strength: int = Field(default=0, ge=0, description="Satisfied scoring points")
    maxStrength: int = Field(default=10, description="Total possible scoring points")
    price: float
    trend_5m: Literal["BULLISH", "BEARISH", "RANGE"] = "RANGE"
    structure_1m: Literal["BULLISH", "BEARISH", "RANGE"] = "RANGE"
    reasons: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    indicators: SignalIndicators = Field(default_factory=SignalIndicators)
    supportLevels: List[PriceLevel] = Field(default_factory=list)
    resistanceLevels: List[PriceLevel] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    symbol: str
    signal: MarketSignal
    timestamp: int
