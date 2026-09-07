import pytest
from app.engines.analytics.outcome import OutcomeAnalyzer, ExitReasonEnum


class TestTradeOutcomeAndDeviationEngine:
    def test_clean_winning_trade_outcome(self):
        analyzer = OutcomeAnalyzer()
        outcome = analyzer.evaluate_closed_trade(
            trade_id=101,
            symbol="EURUSD",
            direction="BUY",
            proposed_entry=1.1000,
            actual_entry=1.10002,  # 0.2 pips slip
            proposed_lots=1.0,
            actual_lots=1.0,
            stop_loss=1.0950,      # 50 pips SL
            exit_price=1.1100,     # 100 pips gain (+2R)
            exit_reason=ExitReasonEnum.TAKE_PROFIT,
            pnl_usd=1000.0,
            risk_amount_usd=500.0,
            highest_price_reached=1.1105,
            lowest_price_reached=1.0980,  # went 20.2 pips against actual fill
            duration_seconds=3600.0,
        )

        assert outcome.realized_r_multiple == 2.0
        assert outcome.entry_slippage_pips == 0.2
        assert outcome.mae_pips == 20.2
        assert outcome.mfe_pips == 104.8
        assert outcome.is_disciplined is True
        assert len(outcome.deviation_flags) == 0

    def test_losing_trade_hit_stop_loss(self):
        analyzer = OutcomeAnalyzer()
        outcome = analyzer.evaluate_closed_trade(
            trade_id=102,
            symbol="GBPUSD",
            direction="SELL",
            proposed_entry=1.2500,
            actual_entry=1.2500,
            proposed_lots=2.0,
            actual_lots=2.0,
            stop_loss=1.2550,      # 50 pips SL
            exit_price=1.2550,     # Hit SL (-1R)
            exit_reason=ExitReasonEnum.STOP_LOSS,
            pnl_usd=-1000.0,
            risk_amount_usd=1000.0,
            highest_price_reached=1.2552,
            lowest_price_reached=1.2480,
        )

        assert outcome.realized_r_multiple == -1.0
        assert outcome.is_disciplined is True
        assert outcome.exit_reason == ExitReasonEnum.STOP_LOSS

    def test_lot_size_violation_flagged_as_undisciplined(self):
        analyzer = OutcomeAnalyzer()
        outcome = analyzer.evaluate_closed_trade(
            trade_id=103,
            symbol="EURUSD",
            direction="BUY",
            proposed_entry=1.1000,
            actual_entry=1.1000,
            proposed_lots=1.0,
            actual_lots=3.0,  # Trader 3x over-leveraged!
            stop_loss=1.0950,
            exit_price=1.1100,
            exit_reason=ExitReasonEnum.TAKE_PROFIT,
            pnl_usd=3000.0,
            risk_amount_usd=500.0,
        )

        assert outcome.is_disciplined is False
        assert any("LOT_SIZE_MISMATCH" in f for f in outcome.deviation_flags)

    def test_jpy_pip_multiplier_math(self):
        analyzer = OutcomeAnalyzer()
        outcome = analyzer.evaluate_closed_trade(
            trade_id=104,
            symbol="USDJPY",
            direction="BUY",
            proposed_entry=150.00,
            actual_entry=150.02,  # 2.0 pips slip
            proposed_lots=1.0,
            actual_lots=1.0,
            stop_loss=149.50,
            exit_price=151.00,
            exit_reason=ExitReasonEnum.TAKE_PROFIT,
            pnl_usd=666.0,
            risk_amount_usd=333.0,
            max_allowed_slippage_pips=1.0,
        )

        assert outcome.entry_slippage_pips == 2.0
        assert outcome.is_disciplined is False
        assert any("ENTRY_SLIPPAGE_EXCEEDED" in f for f in outcome.deviation_flags)
