import pytest
from datetime import datetime, timezone, timedelta
from app.core.data_status import DataStatus
from app.services.broker.adapters import (
    PropProviderAdapter,
    check_account_freshness,
    UnverifiedAccountError
)


class TestProviderAdaptersAndFreshness:
    """Test real account state adapter verification, syncing and freshness rules."""

    @pytest.mark.anyio
    async def test_handshake_verification_success(self):
        adapter = PropProviderAdapter("acc_test_999", "valid_secret_token_abc", "https://api.fundingpips.com")
        is_verified = await adapter.verify_handshake()
        assert is_verified is True

    @pytest.mark.anyio
    async def test_handshake_verification_fail_closed(self):
        adapter = PropProviderAdapter("acc_test_999", "short", "https://api.fundingpips.com")
        is_verified = await adapter.verify_handshake()
        assert is_verified is False

    @pytest.mark.anyio
    async def test_stale_token_throws_unverified_error(self):
        # PROX_ERROR token should fail connection
        adapter = PropProviderAdapter("acc_test_999", "PROX_ERROR_KEY", "https://api.fundingpips.com")
        with pytest.raises(UnverifiedAccountError):
            await adapter.fetch_real_state()

    @pytest.mark.anyio
    async def test_fetch_real_state_populates_fresh_timestamps(self):
        adapter = PropProviderAdapter("acc_test_999", "valid_secret_token_abc", "https://api.fundingpips.com")
        data = await adapter.fetch_real_state()
        assert data["is_verified"] is True
        assert data["current_balance"] == 102500.00
        assert isinstance(data["last_synced_at"], datetime)

    def test_freshness_gate_live_state(self):
        now = datetime.now(timezone.utc)
        status, msg = check_account_freshness(now, threshold_seconds=60)
        assert status == DataStatus.LIVE
        assert "fresh" in msg

    def test_freshness_gate_delayed_state(self):
        stale_time = datetime.now(timezone.utc) - timedelta(seconds=120)
        status, msg = check_account_freshness(stale_time, threshold_seconds=60)
        assert status == DataStatus.DELAYED
        assert "stale" in msg

    def test_freshness_gate_unavailable_state(self):
        dead_time = datetime.now(timezone.utc) - timedelta(minutes=15)
        status, msg = check_account_freshness(dead_time, threshold_seconds=60)
        assert status == DataStatus.UNAVAILABLE
        assert "dead" in msg

    def test_freshness_gate_none_state(self):
        status, msg = check_account_freshness(None, threshold_seconds=60)
        assert status == DataStatus.UNAVAILABLE
        assert "Never synced" in msg
