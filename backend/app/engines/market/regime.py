from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Optional
import numpy as np


class MarketRegimeType(str, Enum):
    TRENDING_BULLISH_EXPANSION = "TRENDING_BULLISH_EXPANSION"
    TRENDING_BEARISH_EXPANSION = "TRENDING_BEARISH_EXPANSION"
    RANGING_COMPRESSION = "RANGING_COMPRESSION"
    VOLATILITY_EXPANSION = "VOLATILITY_EXPANSION"
    CHOPPY_NO_TRADE = "CHOPPY_NO_TRADE"


@dataclass
class MarketRegimeResult:
    regime: MarketRegimeType
    confidence_score: float  # 0.0 to 100.0
    trend_slope_pct: float
    atr_volatility_pips: float
    volatility_expansion_ratio: float
    adx_proxy_strength: float
    is_safe_for_trading: bool
    recommended_strategy: str
    reasons: List[str]


class MarketRegimeDetector:
    """
    Deterministic Quantitative Market Regime Classifier (P2-#33).
    Classifies market conditions based on ATR expansion, MA slope dispersion, and Volume distribution.
    """

    @classmethod
    def classify_regime(
        cls,
        candles: List[Dict[str, Any]],
        symbol: str = "EURUSD",
        atr_period: int = 14,
    ) -> MarketRegimeResult:
        if not candles or len(candles) < 25:
            return MarketRegimeResult(
                regime=MarketRegimeType.CHOPPY_NO_TRADE,
                confidence_score=0.0,
                trend_slope_pct=0.0,
                atr_volatility_pips=0.0,
                volatility_expansion_ratio=1.0,
                adx_proxy_strength=0.0,
                is_safe_for_trading=False,
                recommended_strategy="NONE_STAND_ASIDE",
                reasons=["INSUFFICIENT_BARS_FOR_REGIME_CLASSIFICATION"],
            )

        closes = np.array([float(c["close"]) for c in candles])
        highs = np.array([float(c["high"]) for c in candles])
        lows = np.array([float(c["low"]) for c in candles])
        n = len(closes)

        # Pip conversion
        pip_unit = 0.01 if symbol.upper().endswith("JPY") else 0.0001
        if symbol.upper() in ("XAUUSD", "GOLD"):
            pip_unit = 0.1

        # 1. Moving Average Slopes & Trend Dispersion
        sma_20 = np.mean(closes[-20:])
        sma_50 = np.mean(closes[-min(50, n):])
        current_close = closes[-1]

        trend_slope = ((sma_20 - sma_50) / sma_50) * 100.0

        # 2. True Range & ATR Expansion
        tr_list = []
        for i in range(1, n):
            tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
            tr_list.append(tr)

        atr_recent = np.mean(tr_list[-atr_period:]) if len(tr_list) >= atr_period else np.mean(tr_list)
        atr_baseline = np.mean(tr_list) if len(tr_list) > 0 else atr_recent

        atr_pips = round(float(atr_recent / pip_unit), 1)
        vol_expansion_ratio = round(float(atr_recent / atr_baseline), 2) if atr_baseline > 0 else 1.0

        # 3. ADX Proxy Directional Movement
        up_moves = highs[1:] - highs[:-1]
        down_moves = lows[:-1] - lows[1:]
        plus_dm = np.where((up_moves > down_moves) & (up_moves > 0), up_moves, 0.0)
        minus_dm = np.where((down_moves > up_moves) & (down_moves > 0), down_moves, 0.0)

        sum_tr = np.sum(tr_list[-atr_period:]) if len(tr_list) >= atr_period else 1.0
        plus_di = (np.sum(plus_dm[-atr_period:]) / sum_tr) * 100.0 if sum_tr > 0 else 0.0
        minus_di = (np.sum(minus_dm[-atr_period:]) / sum_tr) * 100.0 if sum_tr > 0 else 0.0

        di_diff = abs(plus_di - minus_di)
        di_sum = plus_di + minus_di
        adx_strength = round(float((di_diff / di_sum) * 100.0 if di_sum > 0 else 0.0), 1)

        # ── 4. Deterministic Regime Decision Matrix ──
        reasons = []
        confidence = 70.0

        if vol_expansion_ratio > 1.8:
            regime = MarketRegimeType.VOLATILITY_EXPANSION
            strategy = "VOLATILITY_BREAKOUT_CAUTION"
            safe = True
            reasons.append(f"Volatility expansion detected (ATR ratio {vol_expansion_ratio}x > 1.8x).")
            confidence = min(95.0, 60.0 + vol_expansion_ratio * 15.0)

        elif adx_strength >= 25.0 and trend_slope > 0.05 and current_close > sma_20:
            regime = MarketRegimeType.TRENDING_BULLISH_EXPANSION
            strategy = "TREND_CONTINUATION_BULLISH"
            safe = True
            reasons.append(f"Strong bullish momentum (ADX: {adx_strength}, Slope: +{trend_slope:.2f}%).")
            confidence = min(95.0, 50.0 + adx_strength * 1.2)

        elif adx_strength >= 25.0 and trend_slope < -0.05 and current_close < sma_20:
            regime = MarketRegimeType.TRENDING_BEARISH_EXPANSION
            strategy = "TREND_CONTINUATION_BEARISH"
            safe = True
            reasons.append(f"Strong bearish momentum (ADX: {adx_strength}, Slope: {trend_slope:.2f}%).")
            confidence = min(95.0, 50.0 + adx_strength * 1.2)

        elif adx_strength < 18.0 and vol_expansion_ratio < 1.1:
            regime = MarketRegimeType.RANGING_COMPRESSION
            strategy = "MEAN_REVERSION_SUPPORT_RESISTANCE"
            safe = True
            reasons.append(f"Market compression / ranging behavior (ADX: {adx_strength} < 18.0).")
            confidence = 80.0

        else:
            regime = MarketRegimeType.CHOPPY_NO_TRADE
            strategy = "NONE_STAND_ASIDE"
            safe = False
            reasons.append("Choppy, low-confluence transition phase. No Trade recommended.")
            confidence = 65.0

        return MarketRegimeResult(
            regime=regime,
            confidence_score=round(confidence, 1),
            trend_slope_pct=round(trend_slope, 3),
            atr_volatility_pips=atr_pips,
            volatility_expansion_ratio=vol_expansion_ratio,
            adx_proxy_strength=adx_strength,
            is_safe_for_trading=safe,
            recommended_strategy=strategy,
            reasons=reasons,
        )
