from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MissingRateError(Exception):
    """Raised when currency conversion rate is missing or invalid."""
    pass


class InstrumentSpec(BaseModel):
    """Canonical instrument contract specification."""
    model_config = ConfigDict(extra="allow")
    
    symbol: str = "EUR/USD"
    pip_size: float = 0.0001
    contract_size: float = 100000.0
    quote_currency: str = "USD"
    base_currency: str = "EUR"
    lot_step: float = 0.01
    min_lot: float = 0.01
    max_lot: float = 100.0


class RiskRequest(BaseModel):
    """Canonical request payload for position sizing and risk computation."""
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    account_balance: float = 10000.0
    risk_percent: float = 1.0
    entry_price: float = 1.0850
    entry: Optional[float] = None
    stop_loss: float = 1.0800
    target_price: Optional[float] = None
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None
    take_profit_3: Optional[float] = None
    leverage: float = 30.0
    pip_size: float = 0.0001
    contract_size: float = 100000.0
    quote_currency: str = "USD"
    base_currency: Optional[str] = None
    symbol: Optional[str] = "EUR/USD"
    pair: Optional[str] = None
    account_currency: str = "USD"
    conversion_rate: Optional[float] = None
    lot_step: float = 0.01
    min_lot: float = 0.01
    max_lot: float = 100.0

    def __init__(self, *args, **kwargs):
        if args:
            field_names = [
                "account_balance", "risk_percent", "entry_price", "stop_loss",
                "take_profit_1", "leverage", "pip_size", "contract_size", "quote_currency"
            ]
            for i, val in enumerate(args):
                if i < len(field_names):
                    kwargs[field_names[i]] = val
        if "entry" in kwargs and "entry_price" not in kwargs:
            kwargs["entry_price"] = kwargs["entry"]
        super().__init__(**kwargs)


class AccountRiskResult(BaseModel):
    """Canonical position sizing output."""
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    allowed: bool = True
    account_balance: float = 10000.0
    max_risk_amount: float = 0.0
    risk_amount_usd: float = 0.0
    risk_percent: float = 0.0
    risk_pct: float = 0.0
    sl_pips: float = 0.0
    stop_loss_pips: float = 0.0
    pip_value_usd: float = 0.0
    position_size_lots: float = 0.0
    position_size_units: float = 0.0
    reward_risk_ratio: Optional[float] = None
    rr_tp1: Optional[float] = None
    rr_tp2: Optional[float] = None
    rr_tp3: Optional[float] = None
    potential_loss: float = 0.0
    potential_profit_usd: Optional[float] = None
    violations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    max_allowed_lots: float = 100.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


def normalize_rate_key(pair: str) -> str:
    """Normalize pair formats: EUR/USD, EURUSD, EUR_USD -> EURUSD."""
    return pair.replace("/", "").replace("_", "").upper()


def calculate_pip_value_usd(
    pip_size: float,
    contract_size: float,
    quote_currency: str,
    rates: Optional[Dict[str, float]] = None
) -> float:
    """
    Calculate USD pip value per standard lot.
    Strict fail-closed if rate is missing.
    """
    quote = quote_currency.upper().strip()
    if quote == "USD":
        return float(pip_size * contract_size)

    if rates is None or not rates:
        raise MissingRateError(f"No conversion rate found for quote currency: {quote}")

    normalized_rates = {normalize_rate_key(k): float(v) for k, v in rates.items() if v and float(v) > 0}

    usd_quote_key = f"USD{quote}"
    if usd_quote_key in normalized_rates:
        rate = normalized_rates[usd_quote_key]
        return float((pip_size * contract_size) / rate)

    quote_usd_key = f"{quote}USD"
    if quote_usd_key in normalized_rates:
        rate = normalized_rates[quote_usd_key]
        return float((pip_size * contract_size) * rate)

    for key, rate in normalized_rates.items():
        if key.startswith("USD") and quote in key:
            return float((pip_size * contract_size) / rate)
        if key.endswith("USD") and quote in key:
            return float((pip_size * contract_size) * rate)

    raise MissingRateError(f"No valid USD conversion rate found for {quote} in {list(rates.keys())}")


def clamp_and_step_lots(
    raw_lots: float,
    lot_step: float = 0.01,
    min_lot: float = 0.01,
    max_lot: float = 100.0
) -> float:
    """
    Deterministically floor lots to step size so risk is NEVER exceeded.
    Clamp between min_lot and max_lot.
    """
    if raw_lots <= 0.0:
        return 0.0
    
    step_decimals = max(0, -int(math.floor(math.log10(lot_step)))) if lot_step < 1.0 else 0
    stepped = math.floor(raw_lots / lot_step) * lot_step
    stepped = round(stepped, step_decimals)
    
    if stepped < min_lot:
        return min_lot
    if stepped > max_lot:
        return max_lot
    return stepped


def calculate_position_size(
    request: Any,
    live_rates: Optional[Dict[str, float]] = None,
    **kwargs
) -> AccountRiskResult:
    """
    Canonical deterministic position sizing engine.
    """
    if live_rates is None:
        live_rates = {}

    if isinstance(request, dict):
        req = RiskRequest(**request)
    elif isinstance(request, RiskRequest):
        req = request
    elif hasattr(request, "account_balance"):
        req = RiskRequest(
            account_balance=float(getattr(request, "account_balance", 10000.0)),
            risk_percent=float(getattr(request, "risk_percent", 1.0)),
            entry_price=float(getattr(request, "entry_price", getattr(request, "entry", 1.0850))),
            stop_loss=float(getattr(request, "stop_loss", 1.0800)),
            pip_size=float(getattr(request, "pip_size", 0.0001)),
            contract_size=float(getattr(request, "contract_size", 100000.0)),
            quote_currency=str(getattr(request, "quote_currency", "USD")),
            take_profit_1=getattr(request, "take_profit_1", None),
            take_profit_2=getattr(request, "take_profit_2", None),
            take_profit_3=getattr(request, "take_profit_3", None),
            lot_step=float(getattr(request, "lot_step", 0.01)),
            min_lot=float(getattr(request, "min_lot", 0.01)),
            max_lot=float(getattr(request, "max_lot", 100.0)),
        )
    else:
        req = RiskRequest()

    entry = req.entry or req.entry_price
    sl = req.stop_loss
    tp1 = req.take_profit_1 or req.target_price
    tp2 = req.take_profit_2
    tp3 = req.take_profit_3
    pip_size = max(float(req.pip_size), 1e-6)
    contract_size = float(req.contract_size or 100000.0)

    pip_val_usd = calculate_pip_value_usd(pip_size, contract_size, req.quote_currency, live_rates)

    sl_dist = abs(entry - sl)
    sl_pips = round(sl_dist / pip_size, 2)
    if sl_pips == 0.0:
        sl_pips = 1.0

    max_risk_usd = round(req.account_balance * (req.risk_percent / 100.0), 2)

    raw_lots = max_risk_usd / (sl_pips * pip_val_usd) if (sl_pips * pip_val_usd) > 0 else 0.0
    lots = clamp_and_step_lots(raw_lots, req.lot_step, req.min_lot, req.max_lot)
    units = round(lots * contract_size, 2)

    actual_risk_usd = round(lots * sl_pips * pip_val_usd, 2)

    rr1 = round(abs(tp1 - entry) / sl_dist, 2) if (tp1 and sl_dist > 0) else None
    rr2 = round(abs(tp2 - entry) / sl_dist, 2) if (tp2 and sl_dist > 0) else None
    rr3 = round(abs(tp3 - entry) / sl_dist, 2) if (tp3 and sl_dist > 0) else None

    potential_profit = round(actual_risk_usd * rr1, 2) if rr1 else None

    return AccountRiskResult(
        allowed=True,
        account_balance=req.account_balance,
        max_risk_amount=max_risk_usd,
        risk_amount_usd=actual_risk_usd,
        risk_percent=req.risk_percent,
        risk_pct=req.risk_percent,
        sl_pips=sl_pips,
        stop_loss_pips=sl_pips,
        pip_value_usd=round(pip_val_usd, 4),
        position_size_lots=lots,
        position_size_units=units,
        reward_risk_ratio=rr1,
        rr_tp1=rr1,
        rr_tp2=rr2,
        rr_tp3=rr3,
        potential_loss=actual_risk_usd,
        potential_profit_usd=potential_profit,
        max_allowed_lots=req.max_lot,
        metadata={
            "raw_lots": round(raw_lots, 4),
            "lot_step": req.lot_step,
            "min_lot": req.min_lot,
            "max_lot": req.max_lot,
            "quote_currency": req.quote_currency,
        }
    )
