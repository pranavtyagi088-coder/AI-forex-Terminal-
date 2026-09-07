from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ExitReasonEnum(str, Enum):
    TAKE_PROFIT = "TAKE_PROFIT"
    STOP_LOSS = "STOP_LOSS"
    MANUAL_CLOSE = "MANUAL_CLOSE"
    CIRCUIT_BREAKER_KILL = "CIRCUIT_BREAKER_KILL"
    NEWS_BLACKOUT_FORCE_CLOSE = "NEWS_BLACKOUT_FORCE_CLOSE"
    WEEKEND_ROLLOVER_FORCE_CLOSE = "WEEKEND_ROLLOVER_FORCE_CLOSE"
    SLIPPAGE_ABORT = "SLIPPAGE_ABORT"


class TradeOutcome(BaseModel):
    trade_id: int
    proposal_id: Optional[str] = None
    decision_id: Optional[str] = None
    symbol: str
    direction: str
    
    # Prices & Sizing
    proposed_entry: float
    actual_entry: float
    entry_slippage_pips: float
    proposed_lots: float
    actual_lots: float
    lot_size_deviation: float
    
    exit_price: float
    exit_reason: ExitReasonEnum
    
    # Institutional Metrics
    pnl_usd: float
    realized_r_multiple: float
    risk_amount_usd: float
    mae_pips: float = 0.0  # Maximum Adverse Excursion
    mfe_pips: float = 0.0  # Maximum Favorable Excursion
    duration_seconds: float = 0.0
    
    # Discipline & Compliance
    is_disciplined: bool
    deviation_flags: list[str] = Field(default_factory=list)


class OutcomeAnalyzer:
    """Analyzes closed trade outcomes against original proposals to compute institutional metrics."""

    def _get_pip_multiplier(self, symbol: str) -> float:
        s = symbol.upper()
        if s.endswith("JPY"):
            return 100.0  # 0.01
        elif s in ("XAUUSD", "GOLD"):
            return 10.0   # 0.1
        return 10000.0    # 0.0001

    def evaluate_closed_trade(
        self,
        trade_id: int,
        symbol: str,
        direction: str,
        proposed_entry: float,
        actual_entry: float,
        proposed_lots: float,
        actual_lots: float,
        stop_loss: float,
        exit_price: float,
        exit_reason: ExitReasonEnum,
        pnl_usd: float,
        risk_amount_usd: float,
        proposal_id: Optional[str] = None,
        decision_id: Optional[str] = None,
        highest_price_reached: Optional[float] = None,
        lowest_price_reached: Optional[float] = None,
        duration_seconds: float = 0.0,
        max_allowed_slippage_pips: float = 1.0,
    ) -> TradeOutcome:
        pip_mult = self._get_pip_multiplier(symbol)
        dir_upper = direction.upper()

        # 1. Slippage & Lot Deviations
        entry_slip_pips = round(abs(actual_entry - proposed_entry) * pip_mult, 2)
        lot_dev = round(actual_lots - proposed_lots, 2)

        deviation_flags = []
        if entry_slip_pips > max_allowed_slippage_pips:
            deviation_flags.append(f"ENTRY_SLIPPAGE_EXCEEDED: {entry_slip_pips} pips (Max: {max_allowed_slippage_pips})")

        if abs(lot_dev) > 0.01:
            deviation_flags.append(f"LOT_SIZE_MISMATCH: Actual {actual_lots} vs Proposed {proposed_lots}")

        if exit_reason == ExitReasonEnum.MANUAL_CLOSE:
            deviation_flags.append("MANUAL_EARLY_EXIT: Trade closed manually outside system TP/SL.")

        # 2. Realized R-Multiple Calculation
        sl_distance = abs(proposed_entry - stop_loss)
        if sl_distance > 0 and risk_amount_usd > 0:
            if dir_upper == "BUY":
                price_gain = exit_price - actual_entry
            else:
                price_gain = actual_entry - exit_price
            
            # Strict R-Multiple = Price Gain / Initial Planned SL Distance
            r_multiple = round(price_gain / sl_distance, 2)
        else:
            r_multiple = 0.0

        # 3. MAE / MFE Calculation
        mae_pips = 0.0
        mfe_pips = 0.0

        if highest_price_reached is not None and lowest_price_reached is not None:
            if dir_upper == "BUY":
                max_adverse_move = actual_entry - lowest_price_reached
                max_favorable_move = highest_price_reached - actual_entry
            else:
                max_adverse_move = highest_price_reached - actual_entry
                max_favorable_move = actual_entry - lowest_price_reached

            mae_pips = round(max(0.0, max_adverse_move) * pip_mult, 1)
            mfe_pips = round(max(0.0, max_favorable_move) * pip_mult, 1)

        is_disciplined = len([f for f in deviation_flags if not f.startswith("MANUAL_EARLY_EXIT")]) == 0

        return TradeOutcome(
            trade_id=trade_id,
            proposal_id=proposal_id,
            decision_id=decision_id,
            symbol=symbol.upper(),
            direction=dir_upper,
            proposed_entry=proposed_entry,
            actual_entry=actual_entry,
            entry_slippage_pips=entry_slip_pips,
            proposed_lots=proposed_lots,
            actual_lots=actual_lots,
            lot_size_deviation=lot_dev,
            exit_price=exit_price,
            exit_reason=exit_reason,
            pnl_usd=round(pnl_usd, 2),
            realized_r_multiple=r_multiple,
            risk_amount_usd=risk_amount_usd,
            mae_pips=mae_pips,
            mfe_pips=mfe_pips,
            duration_seconds=duration_seconds,
            is_disciplined=is_disciplined,
            deviation_flags=deviation_flags,
        )
