from typing import Optional, List, Dict, Any
from app.schemas.prop_firm import TradeCheckRequest, TradeCheckResult, AccountHealthScoreSchema
from app.models.prop_firm import AccountState, PropFirmProfile
from app.services.prop_firm.preset_engine import check_news_blackout, check_weekend_holding_risk


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator <= 0.0:
        return 0.0
    return min(100.0, max(0.0, (numerator / denominator) * 100.0))


def get_pip_value(pair: str, lot_size: float) -> float:
    if "JPY" in pair.upper():
        return lot_size * 6.5
    return lot_size * 10.0


def evaluate_trade_risk(
    account: AccountState,
    profile: PropFirmProfile,
    trade: TradeCheckRequest,
    news_items: Optional[List[Dict[str, Any]]] = None
) -> TradeCheckResult:
    violations = []
    warnings = []

    # 1. Calculate Risk in USD
    pip_val = get_pip_value(trade.pair, trade.lot_size)
    risk_amount_usd = round(pip_val * trade.stop_loss_pips, 2)

    starting_bal = float(account.starting_balance)
    risk_pct = round((risk_amount_usd / starting_bal) * 100.0, 2) if starting_bal > 0 else 0.0

    # 2. Daily Loss Check
    daily_limit_usd = float(account.daily_drawdown_limit_usd)
    current_daily_loss = float(account.current_daily_loss_usd)
    remaining_daily_usd = max(0.0, daily_limit_usd - current_daily_loss)
    projected_daily_loss = current_daily_loss + risk_amount_usd
    projected_daily_pct = round((projected_daily_loss / starting_bal) * 100.0, 2) if starting_bal > 0 else 0.0

    if risk_amount_usd > remaining_daily_usd:
        violations.append("EXCEEDS_DAILY_LOSS_LIMIT")

    # 3. Total Max Drawdown Check
    total_limit_usd = float(account.total_drawdown_limit_usd)
    current_total_loss = float(account.current_total_loss_usd)
    remaining_total_usd = max(0.0, total_limit_usd - current_total_loss)
    projected_total_loss = current_total_loss + risk_amount_usd
    projected_total_pct = round((projected_total_loss / starting_bal) * 100.0, 2) if starting_bal > 0 else 0.0

    if risk_amount_usd > remaining_total_usd:
        violations.append("EXCEEDS_MAX_DRAWDOWN_LIMIT")

    # 4. News Blackout Check
    blackout_res = check_news_blackout(news_items, blackout_window_minutes=2)
    if blackout_res["is_blackout"]:
        violations.append("NEWS_BLACKOUT_WINDOW_ACTIVE")
        warnings.append(blackout_res["reason"])

    # 5. Weekend Holding Check
    weekend_res = check_weekend_holding_risk(allow_weekend_holding=False)
    if weekend_res["weekend_breach_risk"]:
        warnings.append(weekend_res["warning"])

    # 6. Warnings for high risk (>2% per trade or >75% buffer used)
    if risk_pct > 2.0:
        warnings.append("HIGH_TRADE_RISK_PERCENTAGE")
    if safe_divide(projected_daily_loss, daily_limit_usd) > 75.0:
        warnings.append("DAILY_LOSS_BUFFER_NEARLY_EXHAUSTED")

    # 7. Max Allowed Lot Size calculation
    max_tolerable_usd = min(remaining_daily_usd, remaining_total_usd)
    max_lot_size = round(max_tolerable_usd / (trade.stop_loss_pips * 10.0), 2) if trade.stop_loss_pips > 0 else 0.0
    max_lot_size = max(0.0, max_lot_size)

    allowed = len(violations) == 0

    return TradeCheckResult(
        allowed=allowed,
        risk_amount_usd=risk_amount_usd,
        risk_pct=risk_pct,
        projected_daily_loss_pct=projected_daily_pct,
        projected_total_loss_pct=projected_total_pct,
        max_allowed_lot_size=max_lot_size,
        violations=violations,
        warnings=warnings
    )


def calculate_account_health(
    account: AccountState,
    profile: PropFirmProfile
) -> AccountHealthScoreSchema:
    daily_used = safe_divide(float(account.current_daily_loss_usd), float(account.daily_drawdown_limit_usd))
    total_used = safe_divide(float(account.current_total_loss_usd), float(account.total_drawdown_limit_usd))

    deduction = (daily_used * 0.5) + (total_used * 0.5)
    score = round(max(0.0, min(100.0, 100.0 - deduction)), 1)

    status = "HEALTHY"
    breach_imminent = False
    recommendations = []

    if score < 40.0:
        status = "CRITICAL"
        breach_imminent = True
        recommendations.append("Halt trading immediately. Maximum drawdown limit is severely compromised.")
    elif score < 70.0:
        status = "CAUTION"
        recommendations.append("Reduce position sizing by 50% to protect account buffer.")
    else:
        recommendations.append("Account metrics are healthy. Standard lot sizing permitted.")

    return AccountHealthScoreSchema(
        score=score,
        status=status,
        daily_loss_used_pct=round(daily_used, 1),
        total_loss_used_pct=round(total_used, 1),
        consecutive_losses=0,
        rule_breach_imminent=breach_imminent,
        recommendations=recommendations
    )
