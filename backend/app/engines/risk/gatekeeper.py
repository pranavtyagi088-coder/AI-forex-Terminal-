from datetime import datetime
from typing import List, Dict, Optional, Any
import math
import logging
from pydantic import BaseModel, Field

from app.engines.risk.correlation import CorrelationRiskEngine, OpenPositionInput, AggregateRiskResult
from app.engines.risk.instruments import InstrumentRegistry, InstrumentSpec, AssetClass
from app.engines.risk.circuit_breaker import CircuitBreakerEngine, BreakerState
from app.services.broker.adapters import check_account_freshness, DataStatus
from app.engines.events.bus import event_bus, EventType, EventSeverity

logger = logging.getLogger("PreFlightGatekeeper")


class PreFlightTradeRequest(BaseModel):
    symbol: str
    direction: str = Field(..., pattern="^(BUY|SELL)$")
    entry_price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    take_profit: Optional[float] = Field(None, gt=0)
    account_balance: float = Field(..., gt=0)
    account_equity: Optional[float] = None
    open_positions: List[OpenPositionInput] = Field(default_factory=list)
    risk_per_trade_pct: float = Field(1.0, gt=0, le=10.0)
    
    # State & Context Controls
    circuit_breaker_state: str = "NORMAL"  # NORMAL, WARNING, RESTRICTED, KILL_SWITCH
    consecutive_losses: int = 0
    account_health_score: float = 100.0
    current_daily_loss_pct: float = 0.0
    current_total_drawdown_pct: float = 0.0
    max_daily_loss_pct: float = 5.0
    max_total_drawdown_pct: float = 10.0
    
    # Freshness & Data Quality
    account_last_synced_at: Optional[datetime] = None
    require_fresh_account_data: bool = False
    freshness_threshold_seconds: int = 60
    
    # Prop Firm Rules
    is_news_blackout: bool = False
    allow_news_trading: bool = False
    is_weekend_window: bool = False
    allow_weekend_holding: bool = False
    
    current_spread_pips: Optional[float] = None
    quotes: Dict[str, float] = Field(default_factory=dict)
    min_lot: Optional[float] = None
    max_lot: Optional[float] = None
    lot_step: Optional[float] = None


class PreFlightTradeResponse(BaseModel):
    allowed: bool
    canonical_symbol: str
    approved_lot_size: float
    risk_amount_usd: float
    risk_pct: float
    pip_risk: float
    reward_risk_ratio: Optional[float] = None
    rejection_reasons: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    gate_checks: Dict[str, bool] = Field(default_factory=dict)
    account_data_status: str = "UNKNOWN"


class PreFlightGatekeeper:
    def __init__(
        self,
        correlation_engine: Optional[CorrelationRiskEngine] = None,
        instrument_registry: Optional[InstrumentRegistry] = None,
        circuit_breaker: Optional[CircuitBreakerEngine] = None,
    ):
        self.correlation_engine = correlation_engine or CorrelationRiskEngine()
        self.instrument_registry = instrument_registry or InstrumentRegistry()
        self.circuit_breaker = circuit_breaker or CircuitBreakerEngine()

    def _calculate_pip_value(self, spec: InstrumentSpec, entry_price: float, quotes: Dict[str, float]) -> float:
        if spec.asset_class == AssetClass.INDEX:
            return 1.0
        elif spec.canonical_symbol in ("XAUUSD", "GOLD"):
            return 10.0
        elif spec.canonical_symbol == "XAGUSD":
            return 50.0
        elif spec.quote_currency == "USD":
            return 10.0
        elif spec.base_currency == "USD":
            rate = quotes.get(spec.canonical_symbol, entry_price)
            if rate <= 0:
                raise ValueError(f"Invalid USD quote conversion rate: {rate}")
            return (spec.contract_size * spec.pip_unit) / rate
        elif spec.canonical_symbol == "EURGBP":
            gbpusd = quotes.get("GBPUSD", 1.25)
            return 10.0 * gbpusd
        elif spec.quote_currency == "JPY":
            usdjpy = quotes.get("USDJPY", 150.0)
            if usdjpy <= 0:
                raise ValueError(f"Invalid USDJPY rate for JPY cross: {usdjpy}")
            return (spec.contract_size * spec.pip_unit) / usdjpy
        return 10.0

    def _sanitize_numerical_inputs(self, req: PreFlightTradeRequest) -> Optional[str]:
        """Deterministic numerical validity guard against NaN, Inf, and float anomalies."""
        numeric_fields = {
            "entry_price": req.entry_price,
            "stop_loss": req.stop_loss,
            "account_balance": req.account_balance,
            "risk_per_trade_pct": req.risk_per_trade_pct,
            "current_daily_loss_pct": req.current_daily_loss_pct,
            "current_total_drawdown_pct": req.current_total_drawdown_pct,
        }
        if req.take_profit is not None:
            numeric_fields["take_profit"] = req.take_profit
        if req.current_spread_pips is not None:
            numeric_fields["current_spread_pips"] = req.current_spread_pips

        for field_name, val in numeric_fields.items():
            if math.isnan(val) or math.isinf(val):
                return f"DATA_FEED_UNCERTAINTY: Field '{field_name}' contains invalid non-numeric float (NaN/Inf)."
        return None

    def evaluate(self, req: PreFlightTradeRequest) -> PreFlightTradeResponse:
        rejection_reasons: List[str] = []
        warnings: List[str] = []
        data_status_str = "LIVE"
        gate_checks = {
            "account_freshness": True,
            "instrument_supported": True,
            "spread_guard": True,
            "circuit_breaker": True,
            "prop_firm_drawdown": True,
            "news_and_calendar": True,
            "stop_loss_geometry": True,
            "portfolio_correlation": True,
        }

        canonical_sym = req.symbol.upper()

        try:
            # ── Pre-Gate: Input Math Sanitization ──
            sanitization_error = self._sanitize_numerical_inputs(req)
            if sanitization_error:
                rejection_reasons.append(sanitization_error)
                return self._fail_closed_response(
                    req=req,
                    canonical_sym=canonical_sym,
                    rejection_reasons=rejection_reasons,
                    gate_checks=gate_checks,
                    account_data_status="UNAVAILABLE",
                )

            # ── 0. Gate: Account Freshness Check ──
            if req.account_last_synced_at is not None:
                data_status, freshness_reason = check_account_freshness(
                    req.account_last_synced_at,
                    threshold_seconds=req.freshness_threshold_seconds,
                )
                data_status_str = data_status.value
                if data_status in (DataStatus.UNAVAILABLE, DataStatus.DELAYED) and req.require_fresh_account_data:
                    rejection_reasons.append(f"STALE_ACCOUNT_DATA: {freshness_reason}")
                    gate_checks["account_freshness"] = False
                elif data_status == DataStatus.DELAYED:
                    warnings.append(f"DELAYED_ACCOUNT_DATA: {freshness_reason}")

            # ── 1. Gate: Instrument Validation & Spec Retrieval ──
            try:
                canonical_sym = self.instrument_registry.normalize_symbol(req.symbol)
                spec = self.instrument_registry.get_spec(req.symbol)
            except Exception as e:
                rejection_reasons.append(f"UNSUPPORTED_INSTRUMENT: {str(e)}")
                gate_checks["instrument_supported"] = False
                return PreFlightTradeResponse(
                    allowed=False,
                    canonical_symbol=canonical_sym,
                    approved_lot_size=0.0,
                    risk_amount_usd=0.0,
                    risk_pct=req.risk_per_trade_pct,
                    pip_risk=0.0,
                    rejection_reasons=rejection_reasons,
                    warnings=warnings,
                    gate_checks=gate_checks,
                    account_data_status=data_status_str,
                )

            # ── 2. Gate: Spread Guard ──
            if req.current_spread_pips is not None:
                if req.current_spread_pips > spec.max_allowed_spread_pips:
                    rejection_reasons.append(
                        f"SPREAD_EXCEEDS_MAX_LIMIT: Current spread {req.current_spread_pips:.1f} pips exceeds limit {spec.max_allowed_spread_pips:.1f} pips."
                    )
                    gate_checks["spread_guard"] = False

            # ── 3. Gate: Server-Side Continuous Circuit Breaker ──
            server_breaker_snap = self.circuit_breaker.evaluate(
                daily_loss_pct=req.current_daily_loss_pct,
                total_dd_pct=req.current_total_drawdown_pct,
                consecutive_losses=req.consecutive_losses,
                health_score=req.account_health_score,
            )

            effective_breaker_state = server_breaker_snap.state.value
            if req.circuit_breaker_state == "KILL_SWITCH":
                effective_breaker_state = "KILL_SWITCH"

            if effective_breaker_state == "KILL_SWITCH":
                rejection_reasons.append(f"Circuit Breaker KILL_SWITCH is active ({server_breaker_snap.reason or 'Halted'}).")
                gate_checks["circuit_breaker"] = False
            elif effective_breaker_state == "RESTRICTED":
                warnings.append("Circuit Breaker RESTRICTED mode active. Reduce risk.")

            # ── 4. Gate: Prop Firm Drawdown Limits ──
            if req.current_daily_loss_pct >= req.max_daily_loss_pct:
                rejection_reasons.append(
                    f"Daily drawdown limit reached ({req.current_daily_loss_pct:.2f}% >= {req.max_daily_loss_pct:.2f}%)."
                )
                gate_checks["prop_firm_drawdown"] = False

            if req.current_total_drawdown_pct >= req.max_total_drawdown_pct:
                rejection_reasons.append(
                    f"Max drawdown limit breached ({req.current_total_drawdown_pct:.2f}% >= {req.max_total_drawdown_pct:.2f}%)."
                )
                gate_checks["prop_firm_drawdown"] = False

            # ── 5. Gate: News & Calendar Restrictions ──
            if req.is_news_blackout and not req.allow_news_trading:
                rejection_reasons.append("High-impact news blackout window is active for this prop firm challenge.")
                gate_checks["news_and_calendar"] = False

            if req.is_weekend_window and not req.allow_weekend_holding:
                warnings.append("Weekend rollover approaching. Firm mandates closing before weekend.")

            # ── 6. Gate: Stop Loss Geometry & Pip Sizing ──
            pip_unit = spec.pip_unit
            price_diff = req.entry_price - req.stop_loss if req.direction == "BUY" else req.stop_loss - req.entry_price
            if price_diff <= 0:
                rejection_reasons.append(
                    f"Invalid Stop Loss geometry: {req.direction} requires SL {'below' if req.direction == 'BUY' else 'above'} entry."
                )
                gate_checks["stop_loss_geometry"] = False
                pip_distance = 0.0
            else:
                pip_distance = price_diff / pip_unit

            risk_usd = req.account_balance * (req.risk_per_trade_pct / 100.0)

            # Risk-to-reward ratio calculation
            rr_ratio: Optional[float] = None
            if req.take_profit and price_diff > 0:
                target_diff = req.take_profit - req.entry_price if req.direction == "BUY" else req.entry_price - req.take_profit
                if target_diff > 0:
                    rr_ratio = round(target_diff / price_diff, 2)
                    if rr_ratio < 1.0:
                        warnings.append(f"Sub-optimal Risk-to-Reward ratio: {rr_ratio}:1 (Recommended >= 1.5:1)")
                else:
                    warnings.append("Take profit is set on wrong side of entry price.")

            # Lot bounds from spec or override
            min_l = req.min_lot or spec.min_lot
            max_l = req.max_lot or spec.max_lot
            step_l = req.lot_step or spec.lot_step

            approved_lot = 0.0
            if pip_distance > 0:
                pip_val = self._calculate_pip_value(spec, req.entry_price, req.quotes)
                raw_lot = risk_usd / (pip_distance * pip_val)
                # Precision guard: round to 7 decimals before floor quantization to neutralize binary float imprecision
                stepped_lot = math.floor(round(raw_lot / step_l, 7)) * step_l
                approved_lot = max(min_l, min(stepped_lot, max_l))
                approved_lot = round(approved_lot, 2)

            # ── 7. Gate: Portfolio & Cluster Correlation ──
            corr_result: AggregateRiskResult = self.correlation_engine.evaluate_aggregate_risk(
                account_balance=req.account_balance,
                open_positions=req.open_positions,
                proposed_symbol=canonical_sym,
                proposed_direction=req.direction,
                proposed_risk_usd=risk_usd,
                proposed_risk_pct=req.risk_per_trade_pct,
            )

            if not corr_result.allowed:
                rejection_reasons.extend(corr_result.violations)
                gate_checks["portfolio_correlation"] = False

            warnings.extend(corr_result.warnings)

            allowed = len(rejection_reasons) == 0 and approved_lot > 0

            # ── 8. EventBus Telemetry Emission ──
            if not allowed:
                event_bus.publish(
                    event_type=EventType.NO_TRADE_DECISION,
                    severity=EventSeverity.WARNING,
                    source_module="PreFlightGatekeeper",
                    symbol=canonical_sym,
                    message=f"Pre-flight trade vetoed for {canonical_sym}: {'; '.join(rejection_reasons)}",
                    payload={"reasons": rejection_reasons, "gate_checks": gate_checks},
                )

            return PreFlightTradeResponse(
                allowed=allowed,
                canonical_symbol=canonical_sym,
                approved_lot_size=approved_lot if allowed else 0.0,
                risk_amount_usd=risk_usd,
                risk_pct=req.risk_per_trade_pct,
                pip_risk=round(pip_distance, 1),
                reward_risk_ratio=rr_ratio,
                rejection_reasons=rejection_reasons,
                warnings=warnings,
                gate_checks=gate_checks,
                account_data_status=data_status_str,
            )

        except Exception as unhandled_exc:
            error_msg = f"SYSTEM_ERROR_FAIL_CLOSED: {type(unhandled_exc).__name__}: {str(unhandled_exc)}"
            logger.error("Unhandled exception during gatekeeper evaluation — enforcing FAIL-CLOSED veto.", exc_info=True)
            rejection_reasons.append(error_msg)
            
            for g in gate_checks:
                gate_checks[g] = False

            event_bus.publish(
                event_type=EventType.SYSTEM_ALERT,
                severity=EventSeverity.CRITICAL,
                source_module="PreFlightGatekeeper",
                symbol=canonical_sym,
                message=f"FAIL-CLOSED Veto triggered due to engine exception: {str(unhandled_exc)}",
                payload={"error": str(unhandled_exc), "error_type": type(unhandled_exc).__name__},
            )

            return PreFlightTradeResponse(
                allowed=False,
                canonical_symbol=canonical_sym,
                approved_lot_size=0.0,
                risk_amount_usd=0.0,
                risk_pct=req.risk_per_trade_pct,
                pip_risk=0.0,
                reward_risk_ratio=None,
                rejection_reasons=rejection_reasons,
                warnings=["System encountered an unhandled exception and failed closed for safety."],
                gate_checks=gate_checks,
                account_data_status="UNAVAILABLE",
            )

    def _fail_closed_response(
        self,
        req: PreFlightTradeRequest,
        canonical_sym: str,
        rejection_reasons: List[str],
        gate_checks: Dict[str, bool],
        account_data_status: str,
    ) -> PreFlightTradeResponse:
        event_bus.publish(
            event_type=EventType.NO_TRADE_DECISION,
            severity=EventSeverity.CRITICAL,
            source_module="PreFlightGatekeeper",
            symbol=canonical_sym,
            message=f"Fail-closed veto triggered for {canonical_sym}: {'; '.join(rejection_reasons)}",
            payload={"reasons": rejection_reasons},
        )
        return PreFlightTradeResponse(
            allowed=False,
            canonical_symbol=canonical_sym,
            approved_lot_size=0.0,
            risk_amount_usd=0.0,
            risk_pct=req.risk_per_trade_pct,
            pip_risk=0.0,
            reward_risk_ratio=None,
            rejection_reasons=rejection_reasons,
            warnings=[],
            gate_checks=gate_checks,
            account_data_status=account_data_status,
        )
