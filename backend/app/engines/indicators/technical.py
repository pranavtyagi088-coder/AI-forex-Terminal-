from dataclasses import dataclass, field
from typing import List, Optional
import pandas as pd
import numpy as np


@dataclass
class TechnicalSnapshot:
    trend_direction: str = "sideways"
    ema_fast: float = 0.0
    ema_slow: float = 0.0
    trend_strength: float = 0.0
    swing_highs: List[float] = field(default_factory=list)
    swing_lows: List[float] = field(default_factory=list)
    swing_high: float = 0.0
    swing_low: float = 0.0
    atr_pct: float = 50.0
    last_close: float = 0.0
    rsi: float = 50.0
    adx: float = 25.0
    atr: float = 0.0015
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_hist: float = 0.0
    macd_histogram: float = 0.0
    bars_used: int = 0
    momentum_direction: str = "neutral"
    volatility_state: str = "normal"
    nearest_resistance: float = 0.0
    nearest_support: float = 0.0
    near_key_level: bool = False
    structure_confirmed: bool = False
    structure_bias: str = "neutral"


def compute_technical_snapshot(df: pd.DataFrame) -> TechnicalSnapshot:
    """Compute technical snapshot from OHLCV DataFrame. Requires >= 60 bars."""
    if df is None or len(df) < 60:
        raise ValueError(f"Need at least 60 bars, got {len(df) if df is not None else 0}")

    df_clean = df.copy()
    df_clean.columns = [str(c).lower() for c in df_clean.columns]

    close = df_clean["close"].astype(float)
    high = df_clean["high"].astype(float) if "high" in df_clean.columns else close.copy()
    low = df_clean["low"].astype(float) if "low" in df_clean.columns else close.copy()
    last_close = float(close.iloc[-1])
    n = len(df_clean)

    # EMAs
    fast_p = min(20, n)
    slow_p = min(50, n)
    ema_fast = float(close.ewm(span=fast_p, adjust=False).mean().iloc[-1])
    ema_slow = float(close.ewm(span=slow_p, adjust=False).mean().iloc[-1])

    diff = ema_fast - ema_slow
    raw_strength = abs(diff) / (last_close if last_close > 0 else 1.0) * 10000.0
    trend_strength = min(100.0, raw_strength)

    # Trend direction (lowercase!)
    if trend_strength < 15.0:
        trend_direction = "sideways"
    elif diff > 0:
        trend_direction = "bullish"
    else:
        trend_direction = "bearish"

    # Momentum
    momentum_direction = trend_direction if trend_direction != "sideways" else "neutral"

    # Swing points
    swing_highs = []
    swing_lows = []
    for i in range(2, n - 2):
        if high.iloc[i] >= high.iloc[i-1] and high.iloc[i] >= high.iloc[i-2] and            high.iloc[i] >= high.iloc[i+1] and high.iloc[i] >= high.iloc[i+2]:
            swing_highs.append(float(high.iloc[i]))
        if low.iloc[i] <= low.iloc[i-1] and low.iloc[i] <= low.iloc[i-2] and            low.iloc[i] <= low.iloc[i+1] and low.iloc[i] <= low.iloc[i+2]:
            swing_lows.append(float(low.iloc[i]))

    swing_high = max(swing_highs) if swing_highs else float(high.max())
    swing_low = min(swing_lows) if swing_lows else float(low.min())

    # ATR & atr_pct
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    atr_series = tr.rolling(window=min(14, n), min_periods=1).mean()
    atr_val = float(atr_series.iloc[-1]) if not atr_series.empty else 0.0015

    if len(atr_series) > 1:
        atr_min = float(atr_series.min())
        atr_max = float(atr_series.max())
        atr_pct = float(((atr_val - atr_min) / (atr_max - atr_min)) * 100.0) if atr_max > atr_min else 50.0
    else:
        atr_pct = 50.0

    # Volatility state
    if atr_pct > 80:
        volatility_state = "extreme"
    elif atr_pct > 60:
        volatility_state = "high"
    elif atr_pct < 20:
        volatility_state = "low"
    else:
        volatility_state = "normal"

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(14, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(14, min_periods=1).mean()
    rs = gain / loss.replace(0, 1e-10)
    rsi = float(100.0 - (100.0 / (1.0 + rs.iloc[-1])))

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist_val = float((macd_line - signal_line).iloc[-1])

    # Structure
    structure_confirmed = trend_strength > 25.0 and trend_direction != "sideways"
    structure_bias = trend_direction if structure_confirmed else "neutral"

    # Key levels
    nearest_resistance = swing_high
    nearest_support = swing_low
    price_range = nearest_resistance - nearest_support if nearest_resistance > nearest_support else 1.0
    near_key_level = (
        abs(last_close - nearest_resistance) / price_range < 0.15 or
        abs(last_close - nearest_support) / price_range < 0.15
    )

    return TechnicalSnapshot(
        trend_direction=trend_direction,
        ema_fast=ema_fast,
        ema_slow=ema_slow,
        trend_strength=round(trend_strength, 2),
        swing_highs=swing_highs[-5:],
        swing_lows=swing_lows[-5:],
        swing_high=swing_high,
        swing_low=swing_low,
        atr_pct=round(atr_pct, 2),
        last_close=last_close,
        rsi=round(rsi, 2),
        adx=round(trend_strength, 2),
        atr=round(atr_val, 5),
        macd=round(float(macd_line.iloc[-1]), 5),
        macd_signal=round(float(signal_line.iloc[-1]), 5),
        macd_hist=round(macd_hist_val, 5),
        macd_histogram=round(macd_hist_val, 5),
        bars_used=n,
        momentum_direction=momentum_direction,
        volatility_state=volatility_state,
        nearest_resistance=nearest_resistance,
        nearest_support=nearest_support,
        near_key_level=near_key_level,
        structure_confirmed=structure_confirmed,
        structure_bias=structure_bias,
    )


class TechnicalAnalysisEngine:
    def __init__(self):
        pass

    def compute(self, df: pd.DataFrame) -> TechnicalSnapshot:
        return compute_technical_snapshot(df)

    def analyze(self, df: pd.DataFrame) -> TechnicalSnapshot:
        return compute_technical_snapshot(df)

    @staticmethod
    def compute_snapshot(df: pd.DataFrame) -> TechnicalSnapshot:
        return compute_technical_snapshot(df)
