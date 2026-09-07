"""
Seed all 16 strategies from the Strategy Intelligence Library.
"""

import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, init_db
from app.models.strategy import Strategy
from app.models.instrument import Instrument

STRATEGIES = [
    {
        "instrument": "EUR/USD",
        "name": "Cross-Sectional & Time-Series Currency Momentum",
        "evidence_grade": "A",
        "lifecycle_status": "CAUTION",
        "rules": {
            "strategy_id": "EURUSD_MOM_01",
            "strategy_type": "momentum",
            "timeframes": ["D1"],
            "sessions": ["ANY"],
            "market_regimes": ["TRENDING_BULLISH", "TRENDING_BEARISH"],
            "entry_conditions": {"long": ["ROC_84 > 0", "ROC_28 > 0", "close > SMA_100"], "short": ["ROC_84 < 0", "ROC_28 < 0", "close < SMA_100"]},
            "stop_conditions": {"type": "ATR_MULTIPLE", "multiple": 2.0, "atr_period": 14},
            "take_profit_conditions": {"type": "SIGNAL_FLIP_OR_RR", "rr_multiple": 3.0},
            "invalidation_rules": ["ROC_84_crosses_zero", "close_crosses_SMA_100", "ADX_14 < 15"],
            "volatility_filters": {"max_atr_percentile": 95},
            "min_acceptable_rr": 2.0
        }
    },
    {
        "instrument": "EUR/USD",
        "name": "Interest-Rate Differential / Carry Positioning",
        "evidence_grade": "A",
        "lifecycle_status": "CAUTION",
        "rules": {
            "strategy_id": "EURUSD_CARRY_01",
            "strategy_type": "carry_macro",
            "timeframes": ["D1"],
            "sessions": ["ANY"],
            "market_regimes": ["RANGING", "TRENDING_BULLISH", "TRENDING_BEARISH"],
            "entry_conditions": {"long": ["rate_diff(ECB,FED) > 0", "atr_percentile < 75"], "short": ["rate_diff(FED,ECB) > 0", "atr_percentile < 75"]},
            "stop_conditions": {"type": "ATR_MULTIPLE", "multiple": 1.5, "atr_period": 14},
            "take_profit_conditions": {"type": "SIGNAL_REVERSAL_OR_TIME_CAP", "max_days": 60},
            "invalidation_rules": ["rate_diff_reverses", "atr_percentile > 90"],
            "volatility_filters": {"max_atr_percentile_entry": 75, "max_atr_percentile_hold": 90},
            "min_acceptable_rr": 1.5
        }
    },
    {
        "instrument": "EUR/USD",
        "name": "Moving-Average Trend-Following (decay-flagged)",
        "evidence_grade": "D",
        "lifecycle_status": "CAUTION",
        "rules": {
            "strategy_id": "EURUSD_TREND_01",
            "strategy_type": "trend_following",
            "timeframes": ["D1"],
            "sessions": ["ANY"],
            "market_regimes": ["TRENDING_BULLISH", "TRENDING_BEARISH"],
            "entry_conditions": {"long": ["EMA_50 crosses_above EMA_200", "ADX_14 >= 25"], "short": ["EMA_50 crosses_below EMA_200", "ADX_14 >= 25"]},
            "stop_conditions": {"type": "ATR_MULTIPLE", "multiple": 2.5, "atr_period": 14},
            "take_profit_conditions": {"type": "TRAILING_EMA_50"},
            "invalidation_rules": ["close_crosses_EMA_50", "ADX_14 < 20"],
            "min_acceptable_rr": 1.5
        }
    },
    {
        "instrument": "EUR/USD",
        "name": "PPP Long-Horizon Valuation Filter",
        "evidence_grade": "A",
        "lifecycle_status": "CAUTION",
        "rules": {
            "strategy_id": "EURUSD_PPP_01",
            "strategy_type": "statistical_macro_filter",
            "timeframes": ["MN1"],
            "sessions": ["N/A"],
            "market_regimes": ["ANY"],
            "entry_conditions": {"note": "bias filter only, not standalone"},
            "stop_conditions": {"type": "NOT_APPLICABLE"},
            "take_profit_conditions": {"type": "NOT_APPLICABLE"},
            "invalidation_rules": ["recompute_monthly"],
            "min_acceptable_rr": 0
        }
    },
    {
        "instrument": "XAU/USD",
        "name": "Real Price / Real Yield Valuation Framework",
        "evidence_grade": "A",
        "lifecycle_status": "CAUTION",
        "rules": {
            "strategy_id": "XAUUSD_REALYIELD_01",
            "strategy_type": "statistical_macro",
            "timeframes": ["W1"],
            "sessions": ["ANY"],
            "market_regimes": ["ANY"],
            "entry_conditions": {"long": ["real_yield_4wk falling", "real_price_zscore <= 1.5"], "short": ["real_yield_4wk rising", "real_price_zscore >= -1.5"]},
            "stop_conditions": {"type": "ATR_MULTIPLE", "multiple": 2.0, "atr_period": 14},
            "take_profit_conditions": {"type": "SIGNAL_FLIP_OR_RR", "rr_multiple": 3.0},
            "invalidation_rules": ["real_yield_reverses", "rolling_90d_corr_positive"],
            "min_acceptable_rr": 2.0
        }
    },
    {
        "instrument": "XAU/USD",
        "name": "Safe-Haven / Risk-Off Event Response",
        "evidence_grade": "A",
        "lifecycle_status": "CAUTION",
        "rules": {
            "strategy_id": "XAUUSD_SAFEHAVEN_01",
            "strategy_type": "volatility_event_driven",
            "timeframes": ["D1"],
            "sessions": ["ANY"],
            "market_regimes": ["HIGH_VOLATILITY_UNCLEAR"],
            "entry_conditions": {"long": ["equity_zscore <= -2.0", "gold_move < 1.0*ATR"], "short": "NOT_SPECIFIED"},
            "stop_conditions": {"type": "ATR_MULTIPLE", "multiple": 1.5, "atr_period": 14},
            "take_profit_conditions": {"type": "TIME_CAP_OR_RR", "max_days": 15, "rr_multiple": 2.0},
            "invalidation_rules": ["equity_recovers", "gold_equity_corr_positive"],
            "volatility_filters": {"required_regime": "HIGH_VOLATILITY_UNCLEAR"},
            "min_acceptable_rr": 1.5
        }
    },
    {
        "instrument": "XAU/USD",
        "name": "Long-Term Trend-Following (Time-Series Momentum)",
        "evidence_grade": "B",
        "lifecycle_status": "CAUTION",
        "rules": {
            "strategy_id": "XAUUSD_TREND_01",
            "strategy_type": "trend_following",
            "timeframes": ["W1"],
            "sessions": ["ANY"],
            "market_regimes": ["TRENDING_BULLISH", "TRENDING_BEARISH"],
            "entry_conditions": {"long": ["ROC_252 > 0", "close > SMA_252"], "short": ["ROC_252 < 0", "close < SMA_252"]},
            "stop_conditions": {"type": "ATR_MULTIPLE", "multiple": 2.5, "atr_period": 14},
            "take_profit_conditions": {"type": "SIGNAL_FLIP"},
            "volatility_filters": {"max_atr_percentile": 95},
            "min_acceptable_rr": 2.0
        }
    },
    {
        "instrument": "XAU/USD",
        "name": "Structural Central-Bank Demand Filter",
        "evidence_grade": "C",
        "lifecycle_status": "CAUTION",
        "rules": {
            "strategy_id": "XAUUSD_CBDEMAND_01",
            "strategy_type": "macro_event_driven_filter",
            "timeframes": ["MN1"],
            "sessions": ["N/A"],
            "market_regimes": ["ANY"],
            "entry_conditions": {"note": "bias filter only"},
            "stop_conditions": {"type": "NOT_APPLICABLE"},
            "take_profit_conditions": {"type": "NOT_APPLICABLE"},
            "invalidation_rules": ["recompute_quarterly"],
            "min_acceptable_rr": 0
        }
    },
    {
        "instrument": "GBP/USD",
        "name": "Cross-Sectional & Time-Series Currency Momentum",
        "evidence_grade": "A",
        "lifecycle_status": "CAUTION",
        "rules": {
            "strategy_id": "GBPUSD_MOM_01",
            "strategy_type": "momentum",
            "timeframes": ["D1"],
            "sessions": ["ANY"],
            "market_regimes": ["TRENDING_BULLISH", "TRENDING_BEARISH"],
            "entry_conditions": {"long": ["ROC_84 > 0", "ROC_28 > 0", "close > SMA_100"], "short": ["ROC_84 < 0", "ROC_28 < 0", "close < SMA_100"]},
            "stop_conditions": {"type": "ATR_MULTIPLE", "multiple": 2.5, "atr_period": 14},
            "take_profit_conditions": {"type": "SIGNAL_FLIP_OR_RR", "rr_multiple": 3.0},
            "invalidation_rules": ["ROC_84_crosses_zero", "close_crosses_SMA_100", "ADX_14 < 15"],
            "volatility_filters": {"max_atr_percentile": 95},
            "min_acceptable_rr": 2.0
        }
    },
    {
        "instrument": "GBP/USD",
        "name": "Interest-Rate Differential / Carry Positioning",
        "evidence_grade": "A",
        "lifecycle_status": "CAUTION",
        "rules": {
            "strategy_id": "GBPUSD_CARRY_01",
            "strategy_type": "carry_macro",
            "timeframes": ["D1"],
            "sessions": ["ANY"],
            "market_regimes": ["RANGING", "TRENDING_BULLISH", "TRENDING_BEARISH"],
            "entry_conditions": {"long": ["rate_diff(BOE,FED) > 0", "atr_percentile < 75"], "short": ["rate_diff(FED,BOE) > 0", "atr_percentile < 75"]},
            "stop_conditions": {"type": "ATR_MULTIPLE", "multiple": 1.5, "atr_period": 14},
            "take_profit_conditions": {"type": "SIGNAL_REVERSAL_OR_TIME_CAP", "max_days": 60},
            "invalidation_rules": ["rate_diff_reverses", "atr_percentile > 90"],
            "volatility_filters": {"max_atr_percentile_entry": 75},
            "min_acceptable_rr": 1.5
        }
    },
    {
        "instrument": "GBP/USD",
        "name": "UK Political/Fiscal Event Risk Premium Response",
        "evidence_grade": "A",
        "lifecycle_status": "CAUTION",
        "rules": {
            "strategy_id": "GBPUSD_POLRISK_01",
            "strategy_type": "event_driven_macro",
            "timeframes": ["D1"],
            "sessions": ["LONDON"],
            "market_regimes": ["ANY"],
            "entry_conditions": {"long": ["event_outcome_better_than_priced", "60min_confirm"], "short": ["event_outcome_worse_than_priced", "60min_confirm"]},
            "stop_conditions": {"type": "ATR_MULTIPLE", "multiple": 2.0, "atr_period": 14},
            "take_profit_conditions": {"type": "VOL_REVERSION"},
            "invalidation_rules": ["60min_reversal", "superseding_event"],
            "min_acceptable_rr": 1.5
        }
    },
    {
        "instrument": "GBP/USD",
        "name": "Current-Account Vulnerability Filter",
        "evidence_grade": "C",
        "lifecycle_status": "CAUTION",
        "rules": {
            "strategy_id": "GBPUSD_CURACCT_01",
            "strategy_type": "statistical_macro_filter",
            "timeframes": ["MN1"],
            "sessions": ["N/A"],
            "market_regimes": ["ANY"],
            "entry_conditions": {"note": "AND-gated bias filter with Strategy 3"},
            "stop_conditions": {"type": "NOT_APPLICABLE"},
            "take_profit_conditions": {"type": "NOT_APPLICABLE"},
            "invalidation_rules": ["recompute_quarterly"],
            "min_acceptable_rr": 0
        }
    },
    {
        "instrument": "USD/JPY",
        "name": "Carry Trade with Crash-Risk Framework",
        "evidence_grade": "A",
        "lifecycle_status": "CAUTION",
        "rules": {
            "strategy_id": "USDJPY_CARRY_01",
            "strategy_type": "carry_macro",
            "timeframes": ["D1"],
            "sessions": ["ANY"],
            "market_regimes": ["RANGING", "TRENDING_BULLISH", "TRENDING_BEARISH"],
            "entry_conditions": {"long": ["rate_diff(FED,BOJ) > 0", "atr_percentile < 70", "vix_percentile < 75"], "short": "NOT_SPECIFIED"},
            "stop_conditions": {"type": "ATR_MULTIPLE", "multiple": 1.5, "atr_period": 14},
            "take_profit_conditions": {"type": "SIGNAL_REVERSAL_VIX_OR_TIME_CAP", "max_days": 60},
            "invalidation_rules": ["rate_diff_reverses", "vix_above_90th", "BOJ_hawkish"],
            "volatility_filters": {"max_atr_percentile_entry": 70, "max_vix_percentile_entry": 75},
            "min_acceptable_rr": 1.5
        }
    },
    {
        "instrument": "USD/JPY",
        "name": "Safe-Haven / Risk-Off Response",
        "evidence_grade": "B",
        "lifecycle_status": "CAUTION",
        "rules": {
            "strategy_id": "USDJPY_SAFEHAVEN_01",
            "strategy_type": "volatility_event_driven",
            "timeframes": ["D1"],
            "sessions": ["ANY"],
            "market_regimes": ["HIGH_VOLATILITY_UNCLEAR"],
            "entry_conditions": {"short": ["vix_zscore >= 2.0", "jpy_move < 1.0*ATR"], "long": "NOT_SPECIFIED"},
            "stop_conditions": {"type": "ATR_MULTIPLE", "multiple": 1.5, "atr_period": 14},
            "take_profit_conditions": {"type": "TIME_CAP_OR_RR", "max_days": 10, "rr_multiple": 2.0},
            "invalidation_rules": ["vix_reverts", "corr_turns_positive"],
            "volatility_filters": {"required_regime": "HIGH_VOLATILITY_UNCLEAR"},
            "min_acceptable_rr": 1.5
        }
    },
    {
        "instrument": "USD/JPY",
        "name": "Cross-Sectional & Time-Series Currency Momentum",
        "evidence_grade": "A",
        "lifecycle_status": "CAUTION",
        "rules": {
            "strategy_id": "USDJPY_MOM_01",
            "strategy_type": "momentum",
            "timeframes": ["D1"],
            "sessions": ["ANY"],
            "market_regimes": ["TRENDING_BULLISH", "TRENDING_BEARISH"],
            "entry_conditions": {"long": ["ROC_84 > 0", "ROC_28 > 0", "close > SMA_100"], "short": ["ROC_84 < 0", "ROC_28 < 0", "close < SMA_100"]},
            "stop_conditions": {"type": "ATR_MULTIPLE", "multiple": 2.0, "atr_period": 14},
            "take_profit_conditions": {"type": "SIGNAL_FLIP_OR_RR", "rr_multiple": 3.0},
            "invalidation_rules": ["ROC_84_crosses_zero", "close_crosses_SMA_100", "ADX_14 < 15"],
            "volatility_filters": {"max_atr_percentile": 95},
            "min_acceptable_rr": 2.0
        }
    },
    {
        "instrument": "USD/JPY",
        "name": "FX Intervention Mean-Reversion",
        "evidence_grade": "B",
        "lifecycle_status": "CAUTION",
        "rules": {
            "strategy_id": "USDJPY_INTERVENTION_01",
            "strategy_type": "event_driven_mean_reversion",
            "timeframes": ["D1"],
            "sessions": ["TOKYO"],
            "market_regimes": ["ANY"],
            "entry_conditions": {"short": ["price_near_MOF_concern", "ROC_5 >= 1.5*ATR"], "long": "NOT_SPECIFIED"},
            "stop_conditions": {"type": "ATR_MULTIPLE_BEYOND_EXTREME", "multiple": 1.5, "atr_period": 14},
            "take_profit_conditions": {"type": "TIME_CAP", "max_days": 10},
            "invalidation_rules": ["price_breaks_extreme", "no_followthrough_3d"],
            "min_acceptable_rr": 1.5
        }
    }
]


async def seed():
    print("Initializing database...")
    await init_db()

    async with AsyncSessionLocal() as session:
        for data in STRATEGIES:
            sid = data["rules"].get("strategy_id", data["name"])
            inst_result = await session.execute(
                select(Instrument).where(Instrument.symbol == data["instrument"])
            )
            inst = inst_result.scalar_one_or_none()
            if not inst:
                print(f"  WARN: Instrument {data['instrument']} not found, skipping {sid}")
                continue

            result = await session.execute(
                select(Strategy).where(
                    Strategy.instrument_id == inst.id,
                    Strategy.name == data["name"]
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"  SKIP {sid} (already exists)")
                continue

            strategy = Strategy(
                instrument_id=inst.id,
                name=data["name"],
                evidence_grade=data["evidence_grade"],
                rules=data["rules"],
                lifecycle_status=data["lifecycle_status"],
            )
            session.add(strategy)
            print(f"  ADD  {sid}")

        await session.commit()
    print("Strategy seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed())



