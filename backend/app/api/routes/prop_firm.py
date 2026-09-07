from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.prop_firm import PropFirmProfile, AccountState
from app.schemas.prop_firm import (
    PropFirmProfileSchema,
    AccountStateSchema,
    TradeCheckRequest,
    TradeCheckResult,
    AccountHealthScoreSchema
)
from app.services.risk_evaluator import evaluate_trade_risk, calculate_account_health

router = APIRouter(prefix="/api", tags=["Funded Account Risk"])

@router.get("/prop-firm-profiles/{profile_id}", response_model=PropFirmProfileSchema)
async def get_prop_firm_profile(profile_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PropFirmProfile).where(PropFirmProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if not profile:
        # Default seeding if not found for initial setup
        profile = PropFirmProfile(
            id=profile_id,
            name=profile_id.replace("_", " ").title(),
            daily_drawdown_pct=5.0,
            max_drawdown_pct=10.0,
            drawdown_type="STATIC",
            max_loss_basis="BALANCE",
            profit_target_pct=8.0,
            min_trading_days=0
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile

@router.put("/prop-firm-profiles/{profile_id}", response_model=PropFirmProfileSchema)
async def update_prop_firm_profile(
    profile_id: str,
    payload: PropFirmProfileSchema,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(PropFirmProfile).where(PropFirmProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = PropFirmProfile(id=profile_id)
        db.add(profile)

    profile.name = payload.name
    profile.daily_drawdown_pct = payload.daily_drawdown_pct
    profile.max_drawdown_pct = payload.max_drawdown_pct
    profile.drawdown_type = payload.drawdown_type
    profile.max_loss_basis = payload.max_loss_basis
    profile.profit_target_pct = payload.profit_target_pct
    profile.min_trading_days = payload.min_trading_days

    await db.commit()
    await db.refresh(profile)
    return profile

@router.get("/accounts/{account_id}/state", response_model=AccountStateSchema)
async def get_account_state(account_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AccountState).where(AccountState.account_id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        # Seed initial default 100k account
        account = AccountState(
            account_id=account_id,
            profile_id="funding_pips_100k",
            starting_balance=100000.0,
            current_balance=100000.0,
            current_equity=100000.0,
            daily_starting_equity=100000.0,
            high_water_mark=100000.0,
            daily_drawdown_limit_usd=5000.0,
            total_drawdown_limit_usd=10000.0,
            current_daily_loss_usd=0.0,
            current_total_loss_usd=0.0,
            status="ACTIVE"
        )
        db.add(account)
        await db.commit()
        await db.refresh(account)
    return account

@router.post("/accounts/{account_id}/trade-check", response_model=TradeCheckResult)
async def perform_trade_check(
    account_id: str,
    trade: TradeCheckRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(AccountState).where(AccountState.account_id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        account = AccountState(
            account_id=account_id,
            profile_id="funding_pips_100k",
            starting_balance=100000.0,
            current_balance=100000.0,
            current_equity=100000.0,
            daily_starting_equity=100000.0,
            high_water_mark=100000.0,
            daily_drawdown_limit_usd=5000.0,
            total_drawdown_limit_usd=10000.0
        )
        db.add(account)
        await db.commit()
        await db.refresh(account)

    prof_result = await db.execute(select(PropFirmProfile).where(PropFirmProfile.id == account.profile_id))
    profile = prof_result.scalar_one_or_none()
    if not profile:
        profile = PropFirmProfile(id=account.profile_id, name="Default 100k")
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    return evaluate_trade_risk(account, profile, trade)

@router.get("/accounts/{account_id}/health", response_model=AccountHealthScoreSchema)
async def get_account_health(account_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AccountState).where(AccountState.account_id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        account = AccountState(
            account_id=account_id,
            profile_id="funding_pips_100k",
            starting_balance=100000.0,
            current_balance=100000.0,
            current_equity=100000.0,
            daily_starting_equity=100000.0,
            high_water_mark=100000.0,
            daily_drawdown_limit_usd=5000.0,
            total_drawdown_limit_usd=10000.0
        )
        db.add(account)
        await db.commit()
        await db.refresh(account)

    prof_result = await db.execute(select(PropFirmProfile).where(PropFirmProfile.id == account.profile_id))
    profile = prof_result.scalar_one_or_none()
    if not profile:
        profile = PropFirmProfile(id=account.profile_id, name="Default 100k")
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    return calculate_account_health(account, profile)

@router.get("/prop-firm/presets")
async def list_prop_firm_presets():
    """List all standard institutional prop firm profiles (FTMO, The5ers, FundedNext, Alpha Capital)."""
    from app.services.prop_firm.preset_engine import PROP_FIRM_PRESETS
    return list(PROP_FIRM_PRESETS.values())
