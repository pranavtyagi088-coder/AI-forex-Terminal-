import logging
import uuid
from typing import Dict, Any, Optional, List
from types import SimpleNamespace

from app.services.market.data_service import MarketDataService
from app.services.ai.chart_analyzer import ChartAnalyzer
from app.engines.strategy.market_state import MarketStateAnalyzer
from app.engines.scoring.score_engine import calculate_confluence_score
from app.engines.scoring.no_trade_engine import evaluate_no_trade
from app.engines.risk.calculator import calculate_position_size, RiskRequest
from app.engines.structure.structure_engine import MarketStructureEngine
from app.engines.liquidity.liquidity_engine import LiquidityEngine
from app.engines.strategy.smc_strategy_matcher import rank_all_strategies

logger = logging.getLogger(__name__)

class MarketIntelligenceOrchestrator:
    def __init__(self):
        self.ai_analyzer = ChartAnalyzer()

    async def run_analysis(
        self,
        symbol: str,
        timeframe: str = "15",
        direction: str = "BUY",
        image_paths: Optional[List[str]] = None,
        technical_context: Optional[Dict[str, Any]] = None,
        account_balance: float = 100000.0,
        risk_percent: float = 1.0,
        db: Optional[Any] = None,
        decay_map: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        analysis_id = str(uuid.uuid4())
        logger.info(f"Starting SMC Orchestration {analysis_id} for {symbol} {timeframe} {direction}")

        # 1. Fetch live candles & price
        candles = await MarketDataService.get_candles(symbol, interval=timeframe, limit=50)
        current_price = await MarketDataService.get_price(symbol)
        if current_price is None or current_price == 0:
            current_price = 1.0850

        # 2. Market State & Technical Context
        market_state = MarketStateAnalyzer.analyze(symbol, candles)
        atr = market_state.get("atr", 0.0015)
        if atr <= 0:
            atr = 0.0015

        # 3. SMC Structure & Liquidity Engine Calculations
        structure_data = MarketStructureEngine.analyze_structure(candles)
        liquidity_data = LiquidityEngine.analyze_liquidity(candles)

        # 4. Deterministic Strategy Matching & Decay
        direction_upper = direction.upper()
        active_decay_map = decay_map or {}
        if not active_decay_map and db is not None:
            try:
                from app.engines.strategy.decay_sync import build_decay_map_from_db
                active_decay_map = await build_decay_map_from_db(db)
            except Exception as e:
                logger.warning(f"Failed to query DB decay map: {e}")
                active_decay_map = {}

        strategy_eval = rank_all_strategies(
            market_state=market_state,
            structure_data=structure_data,
            liquidity_data=liquidity_data,
            direction=direction_upper,
            decay_map=active_decay_map
        )
        best_strat = strategy_eval.get("best_strategy")
        strategy_ranking = strategy_eval.get("strategy_ranking", [])

        # 5. Dynamic Stop Loss & Take Profit
        if direction_upper == "BUY":
            stop_loss = round(current_price - (2.0 * atr), 5)
            take_profit = round(current_price + (4.0 * atr), 5)
        else:
            stop_loss = round(current_price + (2.0 * atr), 5)
            take_profit = round(current_price - (4.0 * atr), 5)

        # 6. Position Sizing & Risk Calculation
        risk_req = RiskRequest(
            account_balance=account_balance,
            risk_percent=risk_percent,
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

        raw_dollars = getattr(sizing, "risk_amount_usd", None) or (account_balance * risk_percent / 100.0)
        risk_dollars = float(raw_dollars)

        raw_sl_pips = getattr(sizing, "stop_loss_pips", None) or getattr(sizing, "sl_pips", None) or 20.0
        sl_pips = float(raw_sl_pips)
        tp_pips = round(sl_pips * rr_ratio, 1)

        # 7. Combined Context for Multimodal AI
        combined_context = {
            "symbol": symbol,
            "timeframe": timeframe,
            "direction": direction_upper,
            "current_price": current_price,
            "regime": market_state.get("regime", "UNKNOWN"),
            "session": market_state.get("active_session", "UNKNOWN"),
            "atr": atr,
            "rsi": market_state.get("rsi", 50.0),
            "structure_bias": structure_data.get("structure_bias", "NEUTRAL"),
            "last_structure_event": structure_data.get("last_event", "NONE"),
            "unmitigated_fvgs": liquidity_data.get("unmitigated_fvg_count", 0),
            "best_matched_strategy": best_strat.get("name") if best_strat else "None",
            "strategy_match_score": best_strat.get("final_strategy_score") if best_strat else 0,
            "user_technical_context": technical_context or {}
        }

        # 8. AI Visual & Contextual Analysis
        image_b64 = None
        if image_paths and len(image_paths) > 0:
            from app.services.ai.vision_adapter import VisionAdapter
            encoded, _ = VisionAdapter.encode_file_to_base64(image_paths[0])
            if encoded:
                image_b64 = encoded

        ai_result = await self.ai_analyzer.analyze(
            base64_image=image_b64,
            market_context=combined_context
        )

        ai_confidence = float(ai_result.get("confidence", 0.65))
        ai_bias = str(ai_result.get("bias", direction_upper)).upper()
        ai_summary = str(ai_result.get("summary", "AI analysis complete."))

        # 9. Scoring & Confluence
        trend_direction = "bullish" if direction_upper == "BUY" else "bearish"
        snap = SimpleNamespace(trend_direction=trend_direction, atr=atr)
        ai_agrees = (ai_bias == direction_upper)
        
        scoring_res = calculate_confluence_score(snap=snap, ai_agrees=ai_agrees)
        score_total = getattr(scoring_res, "total_score", getattr(scoring_res, "total", 65.0))

        # 10. No-Trade & Safety Evaluation (Final Authority)
        no_trade_res = evaluate_no_trade(result=scoring_res, snap=snap, rr_ratio=rr_ratio)
        should_trade = getattr(no_trade_res, "should_trade", True)
        no_trade_reasons = getattr(no_trade_res, "reasons", [])

        final_direction = direction_upper
        if not should_trade:
            final_direction = "NO_TRADE"

        return {
            "id": analysis_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "direction": final_direction,
            "confidence": ai_confidence,
            "bias": ai_bias,
            "score_total": score_total,
            "risk_reward_ratio": rr_ratio,
            "rr_ratio": rr_ratio,
            "summary": ai_summary,
            "no_trade_reasons": no_trade_reasons,
            "chart_images": image_paths or [],
            "position_sizing": {
                "position_size_lots": sizing.position_size_lots,
                "risk_amount_dollars": risk_dollars,
                "risk_reward_ratio": rr_ratio,
                "stop_loss_pips": sl_pips,
                "take_profit_pips": tp_pips,
                "entry_price": current_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit
            },
            "market_state": market_state,
            "structure": structure_data,
            "liquidity": liquidity_data,
            "strategy_intelligence": {
                "best_strategy": best_strat,
                "strategy_ranking": strategy_ranking,
                "best_strategy_name": strategy_eval.get("best_strategy_name"),
                "best_strategy_score": strategy_eval.get("best_strategy_score"),
                "evaluated_count": strategy_eval.get("evaluated_count", 0)
            }
        }
