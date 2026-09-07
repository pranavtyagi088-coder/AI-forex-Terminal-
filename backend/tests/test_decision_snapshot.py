import pytest
from app.engines.decision.snapshot import DecisionAuditTrailEngine, NoTradeReasonEnum


class TestDecisionSnapshotAndAuditTrail:
    def test_record_trade_proposal_decision(self):
        engine = DecisionAuditTrailEngine()
        snapshot = engine.record_decision(
            symbol="EURUSD",
            direction="BUY",
            decision_type="TRADE_PROPOSAL",
            proposal_id="PROP-123456",
            market_snapshot={"current_price": 1.1000, "atr_14": 0.0045, "session": "LONDON"},
            evidence_snapshot={"bos_detected": True, "liquidity_sweep": True, "confluence_score": 85.0},
            risk_snapshot={"approved_lots": 1.5, "risk_usd": 1000.0, "risk_pct": 1.0},
            compliance_snapshot={"circuit_breaker": "NORMAL", "daily_dd_pct": 0.5},
            strategy_snapshot={"name": "London Sweep Reversal", "decay_state": "HEALTHY"},
            ai_sidecar_snapshot={"confidence_bonus": 5, "notes": "Strong structural alignment"},
        )

        assert snapshot.decision_id.startswith("DEC-")
        assert snapshot.integrity_hash != ""
        assert snapshot.decision_type == "TRADE_PROPOSAL"
        assert snapshot.market_snapshot["session"] == "LONDON"
        assert engine.verify_integrity(snapshot.decision_id) is True

    def test_record_no_trade_decision_with_taxonomy(self):
        engine = DecisionAuditTrailEngine()
        reasons = [
            NoTradeReasonEnum.CIRCUIT_BREAKER_ACTIVE,
            NoTradeReasonEnum.CLUSTER_OVEREXPOSURE,
        ]
        snapshot = engine.record_decision(
            symbol="GBPUSD",
            direction="BUY",
            decision_type="NO_TRADE",
            no_trade_reasons=reasons,
            risk_snapshot={"cluster_exposure_usd": 6.0, "limit": 3.0},
        )

        assert snapshot.decision_type == "NO_TRADE"
        assert NoTradeReasonEnum.CIRCUIT_BREAKER_ACTIVE in snapshot.no_trade_reasons
        assert NoTradeReasonEnum.CLUSTER_OVEREXPOSURE in snapshot.no_trade_reasons
        assert engine.verify_integrity(snapshot.decision_id) is True

    def test_tampered_snapshot_fails_integrity_verification(self):
        engine = DecisionAuditTrailEngine()
        snapshot = engine.record_decision(
            symbol="EURUSD",
            direction="BUY",
            decision_type="TRADE_PROPOSAL",
            risk_snapshot={"approved_lots": 1.0},
        )

        # Tampering with internal snapshot data directly
        snapshot.risk_snapshot["approved_lots"] = 99.0  # Unauthorized modification
        assert engine.verify_integrity(snapshot.decision_id) is False

    def test_list_recent_snapshots_chronological_order(self):
        engine = DecisionAuditTrailEngine()
        d1 = engine.record_decision(symbol="EURUSD", direction="BUY", decision_type="TRADE_PROPOSAL")
        d2 = engine.record_decision(symbol="GBPUSD", direction="SELL", decision_type="NO_TRADE")
        
        recent = engine.list_recent(limit=10)
        assert len(recent) == 2
        assert recent[0].decision_id == d2.decision_id
        assert recent[1].decision_id == d1.decision_id
