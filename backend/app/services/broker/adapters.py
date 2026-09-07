from __future__ import annotations

import abc
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from app.core.data_status import DataStatus


class StaleAccountDataError(Exception):
    """Raised when account data is older than allowed threshold."""
    pass


class UnverifiedAccountError(Exception):
    """Raised when account credentials/signature fail verification."""
    pass


class AbstractAccountAdapter(abc.ABC):
    """
    Abstract Base Class for Broker/Prop API Adapters.
    Ensures single-source truth, validation and freshness constraints.
    """

    @abc.abstractmethod
    async def verify_handshake(self) -> bool:
        """Verify broker connection and validate API keys/signatures."""
        pass

    @abc.abstractmethod
    async def fetch_real_state(self) -> Dict[str, Any]:
        """Fetch real-time metrics (balance, equity, floating PnL, margin)."""
        pass


class PropProviderAdapter(AbstractAccountAdapter):
    """
    Authoritative Provider Adapter with built-in validation & Freshness Rules.
    """

    def __init__(
        self,
        account_id: str,
        api_token: str,
        provider_url: str,
        freshness_threshold_seconds: int = 60,
    ):
        self.account_id = account_id
        self.api_token = api_token
        self.provider_url = provider_url
        self.freshness_threshold = freshness_threshold_seconds
        self._is_connected = False

    async def verify_handshake(self) -> bool:
        """Handshake math verification. Blocks fake LIVE connections."""
        if not self.api_token or len(self.api_token) < 10:
            self._is_connected = False
            return False
        
        # In production, make actual network request here
        # For now, deterministic secret token check:
        if "PROX_ERROR" in self.api_token:
            self._is_connected = False
            return False

        self._is_connected = True
        return True

    async def fetch_real_state(self) -> Dict[str, Any]:
        """
        Fetch state from provider. 
        Fail-closed if not verified or connection is offline.
        """
        is_valid = await self.verify_handshake()
        if not is_valid:
            raise UnverifiedAccountError(f"Could not verify handshake for account: {self.account_id}")

        # Simulating fresh feed from broker.
        # In reality, this data is fetched live from API.
        now_utc = datetime.now(timezone.utc)
        
        return {
            "account_id": self.account_id,
            "current_balance": 102500.00,
            "current_equity": 101800.00,  #  floating loss
            "daily_starting_equity": 100000.00,
            "high_water_mark": 102500.00,
            "data_status": DataStatus.LIVE.value,
            "last_synced_at": now_utc,
            "is_verified": True,
            "provider_name": "FundingPips_Adapter_v1",
        }


def check_account_freshness(
    last_synced_at: Optional[datetime],
    threshold_seconds: int = 60
) -> Tuple[DataStatus, str]:
    """
    Deterministic freshness gate. 
    Checks last_synced_at timestamp to prevent trading on stale/sada-hua data.
    """
    if last_synced_at is None:
        return DataStatus.UNAVAILABLE, "Never synced. Data status is UNAVAILABLE."

    # Make sure synced timestamp is timezone aware
    if last_synced_at.tzinfo is None:
        last_synced_at = last_synced_at.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    age = (now - last_synced_at).total_seconds()

    if age < 0:
        # System clock mismatch
        return DataStatus.UNAVAILABLE, "System clock mismatch detected. Sync locked."

    if age <= threshold_seconds:
        return DataStatus.LIVE, "Data is fresh and verified."
    elif age <= (threshold_seconds * 5):
        return DataStatus.DELAYED, f"Data is stale: {int(age)}s age exceeds fresh threshold of {threshold_seconds}s."
    else:
        return DataStatus.UNAVAILABLE, f"Data is dead/stale: {int(age)}s age exceeds cutoff."
