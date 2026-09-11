import pytest
from app.engines.market.confluence import apply_zone_evidence_to_confluence

def test_zone_evidence_bullish_support_boosts_buy():
    """Tests that being near a fresh Bullish Order Block boosts a BUY trade confluence by +12."""
    base_score = 60.0
    zone_result = {
        "status": "ACTIVE",
        "top_zones": [
            {
                "zone_type": "BULLISH_ORDER_BLOCK",
                "high": 1.0850,
                "low": 1.0830,
                "score": 85.0,
                "touches": 0,
                "is_mitigated": False,
                "bars_since_creation": 10
            }
        ],
        "evidence_weight": 0.15
    }
    current_price = 1.0840  # Inside bullish zone
    adjusted = apply_zone_evidence_to_confluence(base_score, zone_result, "BUY", current_price)
    assert adjusted == 72.0  # 60 + 12

def test_zone_evidence_bearish_hazard_penalizes_buy():
    """Tests that buying into a strong Bearish resistance zone penalizes score by -10."""
    base_score = 60.0
    zone_result = {
        "status": "ACTIVE",
        "top_zones": [
            {
                "zone_type": "BEARISH_ORDER_BLOCK",
                "high": 1.0950,
                "low": 1.0930,
                "score": 80.0,
                "touches": 0,
                "is_mitigated": False,
                "bars_since_creation": 5
            }
        ],
        "evidence_weight": 0.15
    }
    current_price = 1.0940  # Inside bearish zone
    adjusted = apply_zone_evidence_to_confluence(base_score, zone_result, "BUY", current_price)
    assert adjusted == 50.0  # 60 - 10

def test_zone_evidence_unavailable_or_low_score_ignored():
    """Tests fail-closed rule: UNAVAILABLE or noisy zones don't change base confluence."""
    base_score = 55.0
    unavailable_result = {"status": "UNAVAILABLE", "top_zones": []}
    assert apply_zone_evidence_to_confluence(base_score, unavailable_result, "BUY", 1.0800) == 55.0
    assert apply_zone_evidence_to_confluence(base_score, None, "SELL", 1.0800) == 55.0

    low_score_result = {
        "status": "ACTIVE",
        "top_zones": [{"zone_type": "BULLISH_FVG", "high": 1.085, "low": 1.083, "score": 20.0}]
    }
    assert apply_zone_evidence_to_confluence(base_score, low_score_result, "BUY", 1.084) == 55.0
