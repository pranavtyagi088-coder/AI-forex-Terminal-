from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone


@dataclass
class BrokerAccountInfo:
    account_id: str
    balance: float
    equity: float
    margin: float = 0.0
    free_margin: float = 0.0
    currency: str = "USD"
    leverage: int = 100
    is_connected: bool = True
    server_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class BrokerOrderRequest:
    symbol: str
    direction: str  # "BUY" or "SELL"
    lot_size: float
    entry_price: float
    stop_loss: float  # Mandatory for institutional safety
    take_profit: Optional[float] = None
    max_slippage_pips: float = 1.0
    idempotency_key: Optional[str] = None
    comment: str = "AI Terminal Execution"


@dataclass
class ExecutionReceipt:
    success: bool
    ticket: Optional[str] = None
    fill_price: Optional[float] = None
    fill_lots: Optional[float] = None
    slippage_pips: float = 0.0
    error_message: Optional[str] = None
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PositionInfo:
    ticket: str
    symbol: str
    direction: str
    lots: float
    open_price: float
    current_price: float
    stop_loss: float
    take_profit: Optional[float] = None
    unrealized_pnl: float = 0.0


class BaseBrokerAdapter(abc.ABC):
    """
    Universal Institutional Broker Adapter Interface.
    All brokers (MT5, Paper, cTrader) must implement this contract.
    """

    @abc.abstractmethod
    async def connect(self) -> bool:
        pass

    @abc.abstractmethod
    async def disconnect(self) -> None:
        pass

    @abc.abstractmethod
    async def get_account_info(self) -> BrokerAccountInfo:
        pass

    @abc.abstractmethod
    async def get_open_positions(self) -> List[PositionInfo]:
        pass

    @abc.abstractmethod
    async def place_order(self, order: BrokerOrderRequest) -> ExecutionReceipt:
        pass

    @abc.abstractmethod
    async def close_position(self, ticket: str) -> bool:
        pass

    @abc.abstractmethod
    async def get_heartbeat_latency_ms(self) -> float:
        pass
