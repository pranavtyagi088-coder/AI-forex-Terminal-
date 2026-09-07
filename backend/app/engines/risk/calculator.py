from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

class MissingRateError(Exception):
    """Raised when currency conversion rate is missing."""
    pass

class RiskRequest(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)
    account_balance: float = 10000.0
    risk_percent: float = 1.0
    entry_price: float = 1.0850
    entry: Optional[float] = None
    stop_loss: float = 1.0800
    target_price: Optional[float] = None
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None
    leverage: float = 30.0
    pip_size: float = 0.0001
    contract_size: float = 100000.0
    lot_size: float = 1.0
    quote_currency: str = "USD"
    symbol: Optional[str] = "EUR/USD"
    pair: Optional[str] = None
    account_currency: str = "USD"
    conversion_rate: Optional[float] = 1.0

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
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)
    allowed: bool = True
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
    potential_loss: float = 0.0
    potential_profit_usd: Optional[float] = None
    violations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    max_allowed_lots: float = 10.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

def calculate_pip_value_usd(pip_size: float, contract_size: float, quote_currency: str, rates: Optional[Dict[str, float]] = None) -> float:
    if quote_currency == "USD":
        return float(pip_size * contract_size)
    if rates is None or not rates:
        raise MissingRateError(f"No conversion rate found for {quote_currency}")
    
    rate = None
    for k, v in rates.items():
        if quote_currency in k:
            rate = v
            break
    if rate is None or rate == 0:
        raise MissingRateError(f"No conversion rate found for {quote_currency}")
    return float((pip_size * contract_size) / rate)

def calculate_position_size(request: Any, live_rates: Optional[Dict[str, float]] = None, **kwargs) -> AccountRiskResult:
    if live_rates is None:
        live_rates = {}
    if isinstance(request, dict):
        req = RiskRequest(**request)
    elif isinstance(request, RiskRequest):
        req = request
    else:
        req = RiskRequest(
            account_balance=getattr(request, 'account_balance', 10000.0),
            risk_percent=getattr(request, 'risk_percent', 1.0),
            entry_price=getattr(request, 'entry_price', getattr(request, 'entry', 1.0850)),
            stop_loss=getattr(request, 'stop_loss', 1.0800),
            pip_size=getattr(request, 'pip_size', 0.0001),
            contract_size=getattr(request, 'contract_size', 100000.0),
            quote_currency=getattr(request, 'quote_currency', 'USD'),
            take_profit_1=getattr(request, 'take_profit_1', None),
            take_profit_2=getattr(request, 'take_profit_2', None)
        )

    entry = req.entry or req.entry_price
    sl = req.stop_loss
    tp1 = req.take_profit_1 or req.target_price
    tp2 = req.take_profit_2
    pip_size = req.pip_size
    contract_size = req.contract_size or 100000.0
    
    pip_val = calculate_pip_value_usd(pip_size, contract_size, req.quote_currency, live_rates)
    
    sl_diff = abs(entry - sl)
    sl_pips = round(sl_diff / pip_size, 4) if pip_size > 0 else 1.0
    
    max_risk = req.account_balance * (req.risk_percent / 100.0)
    lots = round(max_risk / (sl_pips * pip_val), 4) if (sl_pips * pip_val) > 0 else 0.01
    
    rr1 = round(abs(tp1 - entry) / sl_diff, 4) if (tp1 and sl_diff > 0) else None
    rr2 = round(abs(tp2 - entry) / sl_diff, 4) if (tp2 and sl_diff > 0) else None

    return AccountRiskResult(
        allowed=True,
        max_risk_amount=max_risk,
        risk_amount_usd=max_risk,
        risk_percent=req.risk_percent,
        risk_pct=req.risk_percent,
        sl_pips=sl_pips,
        stop_loss_pips=sl_pips,
        pip_value_usd=pip_val,
        position_size_lots=lots,
        position_size_units=lots * contract_size,
        reward_risk_ratio=rr1,
        rr_tp1=rr1,
        rr_tp2=rr2,
        potential_loss=max_risk,
        potential_profit_usd=max_risk * rr1 if rr1 else None,
        max_allowed_lots=lots * 2
    )
