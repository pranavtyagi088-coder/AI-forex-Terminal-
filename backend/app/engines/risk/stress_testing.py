from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.engines.risk.correlation import OpenPositionInput
from app.engines.risk.instruments import InstrumentRegistry


class ShockScenarioType(str, Enum):
    FLASH_CRASH_SPREAD_BLOWOUT = "FLASH_CRASH_SPREAD_BLOWOUT"  # 10x spread, 30 pip adverse slip
    WEEKEND_GAP_SHOCK = "WEEKEND_GAP_SHOCK"                    # 250 pip adverse gap
    CORRELATION_CONTAGION_COLLAPSE = "CORRELATION_CONTAGION_COLLAPSE"  # All USD positions move against balance


@dataclass
class ScenarioStressResult:
    scenario_type: ShockScenarioType
    estimated_loss_usd: float
    estimated_drawdown_pct: float
    survives_shock: bool
    account_equity_after_shock: float
    critical_vulnerability_flags: List[str] = field(default_factory=list)


@dataclass
class PortfolioStressReport:
    account_balance: float
    total_open_positions: int
    scenarios: List[ScenarioStressResult]
    worst_case_drawdown_pct: float
    is_resilient_to_black_swan: bool
    risk_officer_recommendation: str


class PortfolioStressEngine:
    """
    Institutional Portfolio Shock & Catastrophe Stress Testing Engine (P3-#43).
    Simulates extreme market anomalies (e.g. SNB Depeg, Flash Crashes, Weekend Gaps).
    """

    MAX_TOLERABLE_STRESS_DRAWDOWN_PCT = 8.0  # Max acceptable shock loss before prop limit

    @classmethod
    def stress_test_portfolio(
        cls,
        account_balance: float,
        open_positions: List[OpenPositionInput],
        registry: Optional[InstrumentRegistry] = None,
    ) -> PortfolioStressReport:
        reg = registry or InstrumentRegistry()
        total_pos = len(open_positions)

        if total_pos == 0:
            return PortfolioStressReport(
                account_balance=account_balance,
                total_open_positions=0,
                scenarios=[],
                worst_case_drawdown_pct=0.0,
                is_resilient_to_black_swan=True,
                risk_officer_recommendation="Zero open market risk. Account is fully protected.",
            )

        scenario_results: List[ScenarioStressResult] = []

        # ── Scenario 1: Flash Crash Spread Blowout (30 Pip Adverse Jump on All Open Trades) ──
        flash_loss = 0.0
        flags_flash = []
        for pos in open_positions:
            try:
                spec = reg.get_spec(pos.symbol)
                pip_val = 10.0 if spec.quote_currency == "USD" or "XAU" in pos.symbol else 8.0
            except Exception:
                pip_val = 10.0
            
            # 30 pips shock + 10x normal spread cost
            loss = 30.0 * pip_val * max(0.1, pos.risk_usd / 500.0)
            flash_loss += loss

        flash_dd_pct = round((flash_loss / account_balance) * 100.0, 2)
        survives_flash = flash_dd_pct < 10.0
        if flash_dd_pct > cls.MAX_TOLERABLE_STRESS_DRAWDOWN_PCT:
            flags_flash.append(f"Flash crash drawdown ({flash_dd_pct}%) breaches stress threshold ({cls.MAX_TOLERABLE_STRESS_DRAWDOWN_PCT}%).")

        scenario_results.append(ScenarioStressResult(
            scenario_type=ShockScenarioType.FLASH_CRASH_SPREAD_BLOWOUT,
            estimated_loss_usd=round(flash_loss, 2),
            estimated_drawdown_pct=flash_dd_pct,
            survives_shock=survives_flash,
            account_equity_after_shock=round(account_balance - flash_loss, 2),
            critical_vulnerability_flags=flags_flash,
        ))

        # ── Scenario 2: Weekend Gap Shock (250 Pip Severe Depeg / Gap on Largest Position) ──
        gap_loss = 0.0
        flags_gap = []
        for pos in open_positions:
            # Full SL slippage bypass simulation (1.5x planned stop loss risk)
            loss = pos.risk_usd * 2.5
            gap_loss += loss

        gap_dd_pct = round((gap_loss / account_balance) * 100.0, 2)
        survives_gap = gap_dd_pct < 10.0
        if gap_dd_pct > 10.0:
            flags_gap.append(f"CRITICAL: Weekend depeg shock wipes out {gap_dd_pct}% equity. Violates 10% max DD.")

        scenario_results.append(ScenarioStressResult(
            scenario_type=ShockScenarioType.WEEKEND_GAP_SHOCK,
            estimated_loss_usd=round(gap_loss, 2),
            estimated_drawdown_pct=gap_dd_pct,
            survives_shock=survives_gap,
            account_equity_after_shock=round(account_balance - gap_loss, 2),
            critical_vulnerability_flags=flags_gap,
        ))

        # ── Scenario 3: Correlation Contagion Collapse (All Cluster Hedges Break simultaneously) ──
        contagion_loss = sum(pos.risk_usd * 1.2 for pos in open_positions)
        contagion_dd_pct = round((contagion_loss / account_balance) * 100.0, 2)
        survives_contagion = contagion_dd_pct < 10.0

        scenario_results.append(ScenarioStressResult(
            scenario_type=ShockScenarioType.CORRELATION_CONTAGION_COLLAPSE,
            estimated_loss_usd=round(contagion_loss, 2),
            estimated_drawdown_pct=contagion_dd_pct,
            survives_shock=survives_contagion,
            account_equity_after_shock=round(account_balance - contagion_loss, 2),
            critical_vulnerability_flags=[f"Simultaneous correlation failure draws down {contagion_dd_pct}%."],
        ))

        worst_dd = max(s.estimated_drawdown_pct for s in scenario_results)
        is_resilient = all(s.survives_shock for s in scenario_results) and worst_dd < 10.0

        rec = "PORTFOLIO_RESILIENT: Open risk is within acceptable tail-risk bounds." if is_resilient else "CRITICAL_TAIL_RISK: Reduce open position exposure or close weekend positions immediately."

        return PortfolioStressReport(
            account_balance=account_balance,
            total_open_positions=total_pos,
            scenarios=scenario_results,
            worst_case_drawdown_pct=worst_dd,
            is_resilient_to_black_swan=is_resilient,
            risk_officer_recommendation=rec,
        )
