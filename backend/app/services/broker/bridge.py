from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from app.engines.execution.events import UnifiedEventBus, ExecutionEventType, ExecutionEvent
from app.engines.execution.staging import OrderStagingManager, StagedProposal, ProposalStatus
from app.services.broker.base import BaseBrokerAdapter, BrokerOrderRequest, ExecutionReceipt

logger = logging.getLogger(__name__)

class InstitutionalBrokerBridge:
    def __init__(
        self,
        adapter: BaseBrokerAdapter,
        staging_manager: Optional[OrderStagingManager] = None,
        event_bus: Optional[UnifiedEventBus] = None,
    ):
        self.adapter = adapter
        self.staging = staging_manager or OrderStagingManager()
        self.event_bus = event_bus or UnifiedEventBus()
        self._executed_proposals: set[str] = set()

    async def execute_proposal(
        self,
        proposal_id: str,
        current_market_price: float,
    ) -> ExecutionReceipt:
        # Idempotency check at Bridge level
        if proposal_id in self._executed_proposals:
            return ExecutionReceipt(
                success=False,
                ticket=None,
                fill_price=0.0,
                fill_lots=0.0,
                slippage_pips=0.0,
                error_message=f'Proposal {proposal_id} has already been dispatched to broker (Duplicate Protection).',
            )

        # Retrieve and verify proposal
        prop = self.staging.get_proposal(proposal_id)
        if not prop:
            return ExecutionReceipt(
                success=False,
                ticket=None,
                fill_price=0.0,
                fill_lots=0.0,
                slippage_pips=0.0,
                error_message=f'Proposal {proposal_id} not found in staging.',
            )

        if prop.status != ProposalStatus.PENDING_APPROVAL:
            return ExecutionReceipt(
                success=False,
                ticket=None,
                fill_price=0.0,
                fill_lots=prop.position_size_lots,
                slippage_pips=0.0,
                error_message=f'Cannot execute proposal in status: {prop.status.value}',
            )

        # Slippage validation & approval via OrderStagingManager
        try:
            approved_prop = self.staging.approve_and_verify_slippage(proposal_id, current_market_price)
        except Exception as e:
            logger.error('Slippage verification failed for %s: %s', proposal_id, e)
            return ExecutionReceipt(
                success=False,
                ticket=None,
                fill_price=0.0,
                fill_lots=prop.position_size_lots,
                slippage_pips=0.0,
                error_message=str(e),
            )

        if approved_prop.status != ProposalStatus.APPROVED:
            return ExecutionReceipt(
                success=False,
                ticket=None,
                fill_price=0.0,
                fill_lots=prop.position_size_lots,
                slippage_pips=0.0,
                error_message=approved_prop.rejection_reason or 'Slippage verification rejected.',
            )

        # Prepare BrokerOrderRequest
        order_req = BrokerOrderRequest(
            symbol=approved_prop.symbol,
            direction=approved_prop.direction,
            lot_size=approved_prop.position_size_lots,
            entry_price=approved_prop.entry_price,
            stop_loss=approved_prop.stop_loss,
            take_profit=approved_prop.take_profit,
            max_slippage_pips=approved_prop.max_slippage_pips,
            comment=f'PROP:{proposal_id[:8]}',
        )

        # Dispatch order to broker
        receipt = await self.adapter.place_order(order_req)

        if receipt.success:
            fill_price = receipt.fill_price or order_req.entry_price
            ticket = receipt.ticket or f'MOCK-{datetime.now(timezone.utc).timestamp()}'
            self._executed_proposals.add(proposal_id)
            self.staging.mark_executed(proposal_id, fill_price=fill_price, ticket=ticket)
            
            # Emit Unified Audit Trail Event
            self.event_bus.publish(ExecutionEvent(
                event_type=ExecutionEventType.ORDER_EXECUTED,
                symbol=order_req.symbol,
                data={
                    'proposal_id': proposal_id,
                    'ticket': ticket,
                    'fill_price': fill_price,
                    'slippage_pips': receipt.slippage_pips,
                    'lots': receipt.fill_lots or order_req.lot_size,
                },
                provenance_hash=ticket,
            ))
        else:
            self.event_bus.publish(ExecutionEvent(
                event_type=ExecutionEventType.ORDER_REJECTED,
                symbol=order_req.symbol,
                data={
                    'proposal_id': proposal_id,
                    'error_reason': receipt.error_message,
                },
                provenance_hash=proposal_id,
            ))

        return receipt
