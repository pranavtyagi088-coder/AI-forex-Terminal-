import hashlib
import json
import time
import uuid
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class NoTradeReasonEnum(str, Enum):
    NONE = "NONE"
    CIRCUIT_BREAKER_ACTIVE = "CIRCUIT_BREAKER_ACTIVE"
    PROP_FIRM_DRAWDOWN_LIMIT = "PROP_FIRM_DRAWDOWN_LIMIT"
    NEWS_BLACKOUT_WINDOW = "NEWS_BLACKOUT_WINDOW"
    WEEKEND_ROLLOVER_RESTRICTION = "WEEKEND_ROLLOVER_RESTRICTION"
    CLUSTER_OVEREXPOSURE = "CLUSTER_OVEREXPOSURE"
    PORTFOLIO_RISK_CAP = "PORTFOLIO_RISK_CAP"
    INVALID_SL_GEOMETRY = "INVALID_SL_GEOMETRY"
    SUB_OPTIMAL_RR_RATIO = "SUB_OPTIMAL_RR_RATIO"
    STRATEGY_DEGRADED_OR_SUSPENDED = "STRATEGY_DEGRADED_OR_SUSPENDED"
    HTF_STRUCTURAL_OPPOSITION = "HTF_STRUCTURAL_OPPOSITION"
    INSUFFICIENT_CONFLUENCE_SCORE = "INSUFFICIENT_CONFLUENCE_SCORE"
    STALE_ACCOUNT_STATE = "STALE_ACCOUNT_STATE"
    SLIPPAGE_EXCEEDED = "SLIPPAGE_EXCEEDED"


class DecisionSnapshot(BaseModel):
    decision_id: str
    proposal_id: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)
    symbol: str
    direction: str
    decision_type: str  # "TRADE_PROPOSAL" | "NO_TRADE"
    no_trade_reasons: List[NoTradeReasonEnum] = Field(default_factory=list)
    
    # Context Snapshots
    market_snapshot: Dict[str, Any] = Field(default_factory=dict)
    evidence_snapshot: Dict[str, Any] = Field(default_factory=dict)
    risk_snapshot: Dict[str, Any] = Field(default_factory=dict)
    compliance_snapshot: Dict[str, Any] = Field(default_factory=dict)
    strategy_snapshot: Dict[str, Any] = Field(default_factory=dict)
    ai_sidecar_snapshot: Dict[str, Any] = Field(default_factory=dict)
    
    integrity_hash: str = ""


class DecisionAuditTrailEngine:
    """Creates cryptographically verifiable immutable snapshots of every trading decision."""

    def __init__(self):
        self._snapshots: Dict[str, DecisionSnapshot] = {}

    def _compute_hash(self, data: Dict[str, Any]) -> str:
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def record_decision(
        self,
        symbol: str,
        direction: str,
        decision_type: str,
        proposal_id: Optional[str] = None,
        no_trade_reasons: Optional[List[NoTradeReasonEnum]] = None,
        market_snapshot: Optional[Dict[str, Any]] = None,
        evidence_snapshot: Optional[Dict[str, Any]] = None,
        risk_snapshot: Optional[Dict[str, Any]] = None,
        compliance_snapshot: Optional[Dict[str, Any]] = None,
        strategy_snapshot: Optional[Dict[str, Any]] = None,
        ai_sidecar_snapshot: Optional[Dict[str, Any]] = None,
    ) -> DecisionSnapshot:
        decision_id = f"DEC-{uuid.uuid4().hex[:10].upper()}"
        reasons = no_trade_reasons or []

        raw_data = {
            "decision_id": decision_id,
            "proposal_id": proposal_id,
            "symbol": symbol.upper(),
            "direction": direction.upper(),
            "decision_type": decision_type,
            "no_trade_reasons": [r.value for r in reasons],
            "market": market_snapshot or {},
            "evidence": evidence_snapshot or {},
            "risk": risk_snapshot or {},
            "compliance": compliance_snapshot or {},
            "strategy": strategy_snapshot or {},
            "ai": ai_sidecar_snapshot or {},
        }

        integrity_hash = self._compute_hash(raw_data)

        snapshot = DecisionSnapshot(
            decision_id=decision_id,
            proposal_id=proposal_id,
            timestamp=time.time(),
            symbol=symbol.upper(),
            direction=direction.upper(),
            decision_type=decision_type,
            no_trade_reasons=reasons,
            market_snapshot=market_snapshot or {},
            evidence_snapshot=evidence_snapshot or {},
            risk_snapshot=risk_snapshot or {},
            compliance_snapshot=compliance_snapshot or {},
            strategy_snapshot=strategy_snapshot or {},
            ai_sidecar_snapshot=ai_sidecar_snapshot or {},
            integrity_hash=integrity_hash,
        )

        self._snapshots[decision_id] = snapshot
        return snapshot

    def verify_integrity(self, decision_id: str) -> bool:
        snapshot = self._snapshots.get(decision_id)
        if not snapshot:
            return False

        raw_data = {
            "decision_id": snapshot.decision_id,
            "proposal_id": snapshot.proposal_id,
            "symbol": snapshot.symbol,
            "direction": snapshot.direction,
            "decision_type": snapshot.decision_type,
            "no_trade_reasons": [r.value for r in snapshot.no_trade_reasons],
            "market": snapshot.market_snapshot,
            "evidence": snapshot.evidence_snapshot,
            "risk": snapshot.risk_snapshot,
            "compliance": snapshot.compliance_snapshot,
            "strategy": snapshot.strategy_snapshot,
            "ai": snapshot.ai_sidecar_snapshot,
        }

        expected_hash = self._compute_hash(raw_data)
        return expected_hash == snapshot.integrity_hash

    def get_snapshot(self, decision_id: str) -> Optional[DecisionSnapshot]:
        return self._snapshots.get(decision_id)

    def list_recent(self, limit: int = 50) -> List[DecisionSnapshot]:
        return sorted(self._snapshots.values(), key=lambda s: s.timestamp, reverse=True)[:limit]
