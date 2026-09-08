import time
import uuid
from enum import Enum
from typing import Dict, Optional, List
from pydantic import BaseModel, Field
from app.engines.risk.gatekeeper import PreFlightGatekeeper, PreFlightTradeRequest, PreFlightTradeResponse


class ProposalStatus(str, Enum):
    GENERATED = 'GENERATED'
    PENDING_APPROVAL = 'PENDING_APPROVAL'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'
    EXECUTED = 'EXECUTED'
    EXPIRED = 'EXPIRED'
    CANCELLED = 'CANCELLED'


class StagedProposal(BaseModel):
    proposal_id: str
    decision_id: Optional[str] = None
    integrity_hash: Optional[str] = None
    idempotency_key: str
    symbol: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: Optional[float] = None
    position_size_lots: float
    risk_amount_usd: float
    risk_pct: float
    max_slippage_pips: float = 1.0
    status: ProposalStatus = ProposalStatus.PENDING_APPROVAL
    created_at_ts: float = Field(default_factory=time.time)
    expires_at_ts: float
    rejection_reason: Optional[str] = None
    execution_fill_price: Optional[float] = None
    execution_ticket: Optional[str] = None


class OrderStagingManager:
    def __init__(self, gatekeeper: Optional[PreFlightGatekeeper] = None, ttl_seconds: float = 120.0):
        self.gatekeeper = gatekeeper or PreFlightGatekeeper()
        self.ttl_seconds = ttl_seconds
        self._proposals: Dict[str, StagedProposal] = {}
        self._idempotency_map: Dict[str, str] = {}

    def stage_order(self, req: PreFlightTradeRequest, idempotency_key: str, max_slippage_pips: float = 1.0) -> StagedProposal:
        if idempotency_key in self._idempotency_map:
            existing_id = self._idempotency_map[idempotency_key]
            existing_prop = self._proposals[existing_id]
            if time.time() > existing_prop.expires_at_ts and existing_prop.status == ProposalStatus.PENDING_APPROVAL:
                existing_prop.status = ProposalStatus.EXPIRED
            return existing_prop

        gate_res: PreFlightTradeResponse = self.gatekeeper.evaluate(req)
        now = time.time()
        prop_id = f'PROP-{uuid.uuid4().hex[:8].upper()}'

        if not gate_res.allowed:
            proposal = StagedProposal(
                proposal_id=prop_id,
                decision_id=gate_res.decision_id,
                integrity_hash=gate_res.integrity_hash,
                idempotency_key=idempotency_key,
                symbol=req.symbol.upper(),
                direction=req.direction,
                entry_price=req.entry_price,
                stop_loss=req.stop_loss,
                take_profit=req.take_profit,
                position_size_lots=0.0,
                risk_amount_usd=gate_res.risk_amount_usd,
                risk_pct=gate_res.risk_pct,
                max_slippage_pips=max_slippage_pips,
                status=ProposalStatus.REJECTED,
                created_at_ts=now,
                expires_at_ts=now + self.ttl_seconds,
                rejection_reason='; '.join(gate_res.rejection_reasons),
            )
        else:
            proposal = StagedProposal(
                proposal_id=prop_id,
                decision_id=gate_res.decision_id,
                integrity_hash=gate_res.integrity_hash,
                idempotency_key=idempotency_key,
                symbol=req.symbol.upper(),
                direction=req.direction,
                entry_price=req.entry_price,
                stop_loss=req.stop_loss,
                take_profit=req.take_profit,
                position_size_lots=gate_res.approved_lot_size,
                risk_amount_usd=gate_res.risk_amount_usd,
                risk_pct=gate_res.risk_pct,
                max_slippage_pips=max_slippage_pips,
                status=ProposalStatus.PENDING_APPROVAL,
                created_at_ts=now,
                expires_at_ts=now + self.ttl_seconds,
            )

        self._proposals[prop_id] = proposal
        self._idempotency_map[idempotency_key] = prop_id
        return proposal

    def approve_and_verify_slippage(self, proposal_id: str, current_market_price: float) -> StagedProposal:
        if proposal_id not in self._proposals:
            raise ValueError(f'Proposal ID {proposal_id} not found.')

        prop = self._proposals[proposal_id]

        if prop.status != ProposalStatus.PENDING_APPROVAL:
            raise ValueError(f'Cannot execute proposal in status: {prop.status.value}')

        if time.time() > prop.expires_at_ts:
            prop.status = ProposalStatus.EXPIRED
            prop.rejection_reason = 'Proposal expired before approval.'
            return prop

        sym = prop.symbol.upper()
        pip_unit = 0.01 if sym.endswith('JPY') else 0.0001
        if sym in ('XAUUSD', 'GOLD'):
            pip_unit = 0.1

        drift_pips = abs(current_market_price - prop.entry_price) / pip_unit

        if drift_pips > prop.max_slippage_pips:
            prop.status = ProposalStatus.REJECTED
            prop.rejection_reason = f'Slippage limit breached: price drifted {drift_pips:.1f} pips (Max allowed: {prop.max_slippage_pips} pips).'
            return prop

        prop.status = ProposalStatus.APPROVED
        return prop

    def mark_executed(self, proposal_id: str, fill_price: float, ticket: str) -> StagedProposal:
        if proposal_id not in self._proposals:
            raise ValueError(f'Proposal ID {proposal_id} not found.')
        prop = self._proposals[proposal_id]
        prop.status = ProposalStatus.EXECUTED
        prop.execution_fill_price = fill_price
        prop.execution_ticket = ticket
        return prop

    def get_proposal(self, proposal_id: str) -> Optional[StagedProposal]:
        return self._proposals.get(proposal_id)
