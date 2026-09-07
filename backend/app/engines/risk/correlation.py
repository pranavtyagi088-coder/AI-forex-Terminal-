from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, ConfigDict, Field


# Standard Institutional 30-Day Average Correlation Matrix (FX Majors & Metals)
FX_CORRELATION_MATRIX: Dict[str, Dict[str, float]] = {
    "EURUSD": {"EURUSD": 1.00, "GBPUSD": 0.82, "AUDUSD": 0.75, "NZDUSD": 0.71, "USDCHF": -0.88, "USDJPY": -0.42, "USDCAD": -0.74, "XAUUSD": 0.65},
    "GBPUSD": {"EURUSD": 0.82, "GBPUSD": 1.00, "AUDUSD": 0.70, "NZDUSD": 0.68, "USDCHF": -0.79, "USDJPY": -0.38, "USDCAD": -0.66, "XAUUSD": 0.58},
    "USDCHF": {"EURUSD": -0.88, "GBPUSD": -0.79, "AUDUSD": -0.68, "NZDUSD": -0.64, "USDCHF": 1.00, "USDJPY": 0.48, "USDCAD": 0.70, "XAUUSD": -0.62},
    "USDJPY": {"EURUSD": -0.42, "GBPUSD": -0.38, "AUDUSD": -0.35, "NZDUSD": -0.32, "USDCHF": 0.48, "USDJPY": 1.00, "USDCAD": 0.45, "XAUUSD": -0.40},
    "AUDUSD": {"EURUSD": 0.75, "GBPUSD": 0.70, "AUDUSD": 1.00, "NZDUSD": 0.88, "USDCHF": -0.68, "USDJPY": -0.35, "USDCAD": -0.76, "XAUUSD": 0.72},
    "USDCAD": {"EURUSD": -0.74, "GBPUSD": -0.66, "AUDUSD": -0.76, "NZDUSD": -0.70, "USDCHF": 0.70, "USDJPY": 0.45, "USDCAD": 1.00, "XAUUSD": -0.55},
    "XAUUSD": {"EURUSD": 0.65, "GBPUSD": 0.58, "AUDUSD": 0.72, "NZDUSD": 0.60, "USDCHF": -0.62, "USDJPY": -0.40, "USDCAD": -0.55, "XAUUSD": 1.00},
}


def clean_symbol(symbol: str) -> str:
    """Normalize symbol to standard 6-char string e.g. EUR/USD -> EURUSD."""
    return symbol.replace("/", "").replace("_", "").upper()


def decompose_pair(symbol: str, direction: str) -> Tuple[str, str, str, str]:
    """
    Decompose a trade into long/short currency positions.
    Example: BUY EURUSD -> Long EUR, Short USD
    Example: SELL USDJPY -> Short USD, Long JPY
    """
    clean = clean_symbol(symbol)
    base = clean[:3]
    quote = clean[3:6] if len(clean) >= 6 else "USD"
    dir_norm = direction.upper()

    if dir_norm in ("BUY", "LONG"):
        long_curr = base
        short_curr = quote
    else:
        long_curr = quote
        short_curr = base

    return base, quote, long_curr, short_curr


class OpenPositionInput(BaseModel):
    """Input representation of an active open position."""
    model_config = ConfigDict(extra="allow")
    symbol: str
    direction: str = "BUY"
    position_size_lots: float = 0.1
    risk_amount_usd: float = 100.0
    risk_pct: float = 1.0


class AggregateRiskLimits(BaseModel):
    """Configurable limits for portfolio-level exposure."""
    max_portfolio_risk_pct: float = 5.0      # Max combined open risk across all positions
    max_currency_cluster_risk_pct: float = 3.0 # Max combined risk exposed to any single currency (e.g. USD)
    max_correlated_positions: int = 2        # Max concurrent positions on pairs with |correlation| >= 0.75
    correlation_threshold: float = 0.75      # Coefficient threshold for high correlation check


class AggregateRiskResult(BaseModel):
    """Result of portfolio-level aggregate and correlation analysis."""
    allowed: bool = True
    total_open_risk_usd: float = 0.0
    total_open_risk_pct: float = 0.0
    projected_total_risk_pct: float = 0.0
    currency_exposures_pct: Dict[str, float] = Field(default_factory=dict)
    correlated_pairs_detected: List[str] = Field(default_factory=list)
    violations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class CorrelationRiskEngine:
    """
    Authoritative Portfolio-Level Aggregate Exposure & Correlation Engine.
    """

    def __init__(self, limits: Optional[AggregateRiskLimits] = None):
        self.limits = limits or AggregateRiskLimits()

    def get_correlation(self, symbol_a: str, symbol_b: str) -> float:
        """Get correlation coefficient between two pairs."""
        a = clean_symbol(symbol_a)
        b = clean_symbol(symbol_b)
        if a == b:
            return 1.0
        if a in FX_CORRELATION_MATRIX and b in FX_CORRELATION_MATRIX[a]:
            return FX_CORRELATION_MATRIX[a][b]
        if b in FX_CORRELATION_MATRIX and a in FX_CORRELATION_MATRIX[b]:
            return FX_CORRELATION_MATRIX[b][a]
        return 0.0

    def evaluate_aggregate_risk(
        self,
        account_balance: float,
        open_positions: List[OpenPositionInput],
        proposed_symbol: str,
        proposed_direction: str,
        proposed_risk_usd: float,
        proposed_risk_pct: float,
    ) -> AggregateRiskResult:
        """
        Evaluate if a new trade can safely fit into the existing portfolio
        without breaching single-currency cluster or total portfolio risk limits.
        """
        violations: List[str] = []
        warnings: List[str] = []
        correlated_pairs: List[str] = []

        # 1. Calculate existing open risk
        current_open_risk_usd = sum(pos.risk_amount_usd for pos in open_positions)
        current_open_risk_pct = sum(pos.risk_pct for pos in open_positions)
        projected_total_risk_pct = round(current_open_risk_pct + proposed_risk_pct, 2)
        projected_total_risk_usd = round(current_open_risk_usd + proposed_risk_usd, 2)

        # 2. Total Portfolio Risk Check
        if projected_total_risk_pct > self.limits.max_portfolio_risk_pct:
            violations.append(
                f"EXCEEDS_MAX_PORTFOLIO_RISK: Projected risk {projected_total_risk_pct}% exceeds limit of {self.limits.max_portfolio_risk_pct}%."
            )

        # 3. Currency Cluster Exposure Map
        currency_exposures: Dict[str, float] = {}

        # Add open positions to currency map
        for pos in open_positions:
            base, quote, long_curr, short_curr = decompose_pair(pos.symbol, pos.direction)
            currency_exposures[long_curr] = round(currency_exposures.get(long_curr, 0.0) + pos.risk_pct, 2)
            currency_exposures[short_curr] = round(currency_exposures.get(short_curr, 0.0) + pos.risk_pct, 2)

        # Add proposed position to currency map
        p_base, p_quote, p_long, p_short = decompose_pair(proposed_symbol, proposed_direction)
        projected_long_exposure = round(currency_exposures.get(p_long, 0.0) + proposed_risk_pct, 2)
        projected_short_exposure = round(currency_exposures.get(p_short, 0.0) + proposed_risk_pct, 2)

        currency_exposures[p_long] = projected_long_exposure
        currency_exposures[p_short] = projected_short_exposure

        # Check currency cluster limits
        for curr, exp_pct in currency_exposures.items():
            if exp_pct > self.limits.max_currency_cluster_risk_pct:
                violations.append(
                    f"EXCEEDS_CURRENCY_CLUSTER_LIMIT: Net exposure on '{curr}' is {exp_pct}% (Limit: {self.limits.max_currency_cluster_risk_pct}%)."
                )

        # 4. Correlation Coefficient Cross-Check
        prop_clean = clean_symbol(proposed_symbol)
        correlated_count = 0

        for pos in open_positions:
            pos_clean = clean_symbol(pos.symbol)
            coeff = self.get_correlation(prop_clean, pos_clean)
            abs_coeff = abs(coeff)

            if abs_coeff >= self.limits.correlation_threshold:
                correlated_count += 1
                correlated_pairs.append(f"{pos.symbol} (corr: {coeff:+.2f})")

                # Warning for high positive correlation in same direction
                if coeff >= self.limits.correlation_threshold and pos.direction.upper() == proposed_direction.upper():
                    warnings.append(
                        f"High positive correlation ({coeff:+.2f}) with open trade {pos.symbol} in the same direction."
                    )
                # Warning for high negative correlation in opposite direction (doubled risk)
                elif coeff <= -self.limits.correlation_threshold and pos.direction.upper() != proposed_direction.upper():
                    warnings.append(
                        f"High inverse correlation ({coeff:+.2f}) with opposite trade {pos.symbol} creating synthetic double exposure."
                    )

        if correlated_count >= self.limits.max_correlated_positions:
            violations.append(
                f"EXCEEDS_MAX_CORRELATED_POSITIONS: {correlated_count} existing positions already correlated with {proposed_symbol} (Max: {self.limits.max_correlated_positions})."
            )

        allowed = len(violations) == 0

        return AggregateRiskResult(
            allowed=allowed,
            total_open_risk_usd=projected_total_risk_usd,
            total_open_risk_pct=current_open_risk_pct,
            projected_total_risk_pct=projected_total_risk_pct,
            currency_exposures_pct=currency_exposures,
            correlated_pairs_detected=correlated_pairs,
            violations=violations,
            warnings=warnings
        )
