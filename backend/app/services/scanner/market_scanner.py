from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid
import logging

from app.services.market.data_service import MarketDataService
from app.engines.strategy.market_state import MarketStateAnalyzer
from app.engines.structure.structure_engine import MarketStructureEngine
from app.engines.liquidity.liquidity_engine import LiquidityEngine
from app.engines.strategy.smc_strategy_matcher import rank_all_strategies
from app.engines.scoring.score_engine import calculate_confluence_score
from app.engines.scoring.no_trade_engine import evaluate_no_trade
from app.engines.risk.calculator import calculate_position_size, RiskRequest
from app.engines.strategy.decay_sync import build_decay_map_from_db
from app.services.scanner.ws_manager import ws_manager

logger = logging.getLogger(__name__)

DEFAULT_WATCHLIST = ["EUR/USD", "GBP/USD", "USD/JPY", "GBP/JPY", "AUD/USD"]
DEFAULT_TIMEFRAMES = ["15", "1h"]

ACTIVE_RADAR_SIGNALS: List[Dict[str, Any]] = []
MAX_RADAR_SIGNALS = 50
LAST_SCAN_TIMESTAMP: Optional[str] = None


class MarketScannerService:
    @staticmethod
    async def scan_symbol_timeframe(
        symbol: str,
        timeframe: str = "15",
        db: Optional[Any] = None,
        decay_map: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        try:
            candles = await MarketDataService.get_candles(symbol, interval=timeframe, limit=50)
            if not candles or len(candles) < 20:
                return None

            current_price = await MarketDataService.get_price(symbol)
            if not current_price or current_price <= 0:
                current_price = candles[-1]["close"] if "close" in candles[-1] else 1.0850

            market_state = MarketStateAnalyzer.analyze(symbol, candles)
            structure_data = MarketStructureEngine.analyze_structure(candles)
            liquidity_data = LiquidityEngine.analyze_liquidity(candles)

            atr = market_state.get("atr", 0.0015)
            if atr <= 0:
                atr = 0.0015

            active_decay = decay_map or {}
            if not active_decay and db is not None:
                try:
                    active_decay = await build_decay_map_from_db(db)
                except Exception:
                    active_decay = {}

            best_candidate = None

            for direction in ["BUY", "SELL"]:
                strategy_eval = rank_all_strategies(
                    market_state=market_state,
                    structure_data=structure_data,
                    liquidity_data=liquidity_data,
                    direction=direction,
                    decay_map=active_decay
                )
                best_strat = strategy_eval.get("best_strategy")
                if not best_strat:
                    continue

                if direction == "BUY":
                    stop_loss = round(current_price - (2.0 * atr), 5)
                    take_profit = round(current_price + (4.0 * atr), 5)
                else:
                    stop_loss = round(current_price + (2.0 * atr), 5)
                    take_profit = round(current_price - (4.0 * atr), 5)

                risk_req = RiskRequest(
                    account_balance=10000.0,
                    risk_percent=1.0,
                    symbol=symbol,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
                sizing = calculate_position_size(risk_req)
                raw_rr = getattr(sizing, "reward_risk_ratio", None) or getattr(sizing, "rr_tp1", None) or 2.0
                try:
                    rr_ratio = float(raw_rr)
                except (ValueError, TypeError):
                    rr_ratio = 2.0

                score_detail = calculate_confluence_score(
                    market_state=market_state,
                    ai_confidence=0.85,
                    ai_direction=direction,
                    risk_reward_ratio=rr_ratio,
                    direction=direction,
                    evidence_grade=best_strat.get("evidence_grade", "A"),
                    decay_status=best_strat.get("decay_status", "ACTIVE")
                )

                score_total = score_detail.get("total_score", 0.0)
                no_trade_eval = evaluate_no_trade(
                    score_total=score_total,
                    rr_ratio=rr_ratio,
                    min_score_threshold=60.0,
                    min_rr_threshold=1.5
                )

                if score_total >= 65.0 and not no_trade_eval.get("no_trade", False):
                    candidate = {
                        "id": str(uuid.uuid4())[:8],
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "direction": direction,
                        "strategy_name": best_strat.get("name", "Institutional Strategy"),
                        "strategy_id": best_strat.get("strategy_id", "UNKNOWN"),
                        "score": round(score_total, 1),
                        "rr_ratio": round(rr_ratio, 2),
                        "entry_price": current_price,
                        "stop_loss": stop_loss,
                        "take_profit": take_profit,
                        "regime": market_state.get("regime", "TREND"),
                        "session": market_state.get("active_session", "ACTIVE"),
                        "detected_at": datetime.now(timezone.utc).isoformat(),
                        "status": "ACTIVE"
                    }
                    if not best_candidate or candidate["score"] > best_candidate["score"]:
                        best_candidate = candidate

            return best_candidate

        except Exception as e:
            logger.warning(f"Scanner error on {symbol} {timeframe}: {e}")
            return None

    @classmethod
    async def scan_all(
        cls,
        watchlist: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
        db: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        global LAST_SCAN_TIMESTAMP
        pairs = watchlist or DEFAULT_WATCHLIST
        tfs = timeframes or DEFAULT_TIMEFRAMES

        new_signals = []
        for sym in pairs:
            for tf in tfs:
                sig = await cls.scan_symbol_timeframe(sym, tf, db=db)
                if sig:
                    new_signals.append(sig)

        LAST_SCAN_TIMESTAMP = datetime.now(timezone.utc).isoformat()

        for s in new_signals:
            existing = next((x for x in ACTIVE_RADAR_SIGNALS if x["symbol"] == s["symbol"] and x["timeframe"] == s["timeframe"]), None)
            if existing:
                ACTIVE_RADAR_SIGNALS.remove(existing)
            ACTIVE_RADAR_SIGNALS.insert(0, s)

        while len(ACTIVE_RADAR_SIGNALS) > MAX_RADAR_SIGNALS:
            ACTIVE_RADAR_SIGNALS.pop()

        if new_signals:
            await ws_manager.broadcast({
                "type": "RADAR_SIGNALS_UPDATED",
                "count": len(new_signals),
                "signals": new_signals,
                "scanned_at": LAST_SCAN_TIMESTAMP
            })

        return ACTIVE_RADAR_SIGNALS
