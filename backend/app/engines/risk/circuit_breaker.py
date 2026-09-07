from __future__ import annotations

import enum
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any


class BreakerState(str, enum.Enum):
    """
    Circuit breaker states. Severity increases top to bottom.
    Fail-closed: unknown/unreadable state = KILL_SWITCH.
    """
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    RESTRICTED = "RESTRICTED"
    KILL_SWITCH = "KILL_SWITCH"


# Severity ordering for comparison
_STATE_SEVERITY = {
    BreakerState.NORMAL: 0,
    BreakerState.WARNING: 1,
    BreakerState.RESTRICTED: 2,
    BreakerState.KILL_SWITCH: 3,
}


@dataclass
class BreakerThresholds:
    """
    Configurable thresholds for state transitions.
    All percentages are of starting balance.
    """
    # Daily loss thresholds
    daily_loss_warning_pct: float = 3.0       # 3% daily loss -> WARNING
    daily_loss_restricted_pct: float = 4.0    # 4% daily loss -> RESTRICTED
    daily_loss_kill_pct: float = 4.5          # 4.5% daily loss -> KILL_SWITCH

    # Total drawdown thresholds
    total_dd_warning_pct: float = 6.0         # 6% total DD -> WARNING
    total_dd_restricted_pct: float = 8.0      # 8% total DD -> RESTRICTED
    total_dd_kill_pct: float = 9.0            # 9% total DD -> KILL_SWITCH

    # Consecutive losses
    consecutive_loss_warning: int = 3         # 3 losses in a row -> WARNING
    consecutive_loss_restricted: int = 5      # 5 losses -> RESTRICTED
    consecutive_loss_kill: int = 7            # 7 losses -> KILL_SWITCH

    # Health score (0-100, lower is worse)
    health_warning: float = 60.0
    health_restricted: float = 40.0
    health_kill: float = 20.0


@dataclass
class BreakerSnapshot:
    """Immutable snapshot of breaker state at a point in time."""
    state: BreakerState
    triggered_at: Optional[str] = None
    reason: str = ""
    daily_loss_pct: float = 0.0
    total_dd_pct: float = 0.0
    consecutive_losses: int = 0
    health_score: float = 100.0
    allowed_to_trade: bool = True
    max_risk_multiplier: float = 1.0
    details: List[str] = field(default_factory=list)


# Persistent state file path (survives restarts)
_BREAKER_STATE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "breaker_state.json"
)


class CircuitBreakerEngine:
    """
    System-level circuit breaker.
    
    Monitors account health metrics and transitions between states.
    Fail-closed: if state cannot be determined, assumes KILL_SWITCH.
    
    State transitions are ONE-WAY (can only escalate automatically).
    De-escalation (reset) requires explicit human/admin action.
    """

    def __init__(self, thresholds: Optional[BreakerThresholds] = None):
        self.thresholds = thresholds or BreakerThresholds()
        self._state: BreakerState = BreakerState.NORMAL
        self._reason: str = ""
        self._triggered_at: Optional[datetime] = None
        self._details: List[str] = []
        self._load_persistent_state()

    def _load_persistent_state(self) -> None:
        """Load breaker state from disk. Fail-closed on any error."""
        try:
            if os.path.exists(_BREAKER_STATE_FILE):
                with open(_BREAKER_STATE_FILE, "r") as f:
                    data = json.load(f)
                raw_state = data.get("state", "KILL_SWITCH")
                try:
                    self._state = BreakerState(raw_state)
                except ValueError:
                    self._state = BreakerState.KILL_SWITCH
                self._reason = data.get("reason", "")
                self._details = data.get("details", [])
                ts = data.get("triggered_at")
                if ts:
                    self._triggered_at = datetime.fromisoformat(ts)
        except Exception:
            # Fail-closed: if we can't read state, assume worst
            self._state = BreakerState.KILL_SWITCH
            self._reason = "STATE_READ_FAILURE: Could not load breaker state from disk."

    def _save_persistent_state(self) -> None:
        """Persist breaker state to disk so it survives restarts."""
        try:
            data = {
                "state": self._state.value,
                "reason": self._reason,
                "triggered_at": self._triggered_at.isoformat() if self._triggered_at else None,
                "details": self._details,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(_BREAKER_STATE_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            # If we can't save, escalate to KILL_SWITCH
            self._state = BreakerState.KILL_SWITCH
            self._reason = "STATE_WRITE_FAILURE: Could not persist breaker state."

    @property
    def state(self) -> BreakerState:
        return self._state

    def evaluate(
        self,
        daily_loss_pct: float = 0.0,
        total_dd_pct: float = 0.0,
        consecutive_losses: int = 0,
        health_score: float = 100.0,
    ) -> BreakerSnapshot:
        """
        Evaluate account metrics and determine breaker state.
        
        IMPORTANT: State can only ESCALATE automatically.
        If already in KILL_SWITCH, stays in KILL_SWITCH until manual reset.
        """
        # If already in KILL_SWITCH, don't auto-downgrade
        if self._state == BreakerState.KILL_SWITCH:
            return self._build_snapshot(daily_loss_pct, total_dd_pct, consecutive_losses, health_score)

        reasons: List[str] = []
        new_state = BreakerState.NORMAL

        # --- Check Daily Loss ---
        if daily_loss_pct >= self.thresholds.daily_loss_kill_pct:
            new_state = BreakerState.KILL_SWITCH
            reasons.append(f"Daily loss {daily_loss_pct:.2f}% >= kill threshold {self.thresholds.daily_loss_kill_pct}%")
        elif daily_loss_pct >= self.thresholds.daily_loss_restricted_pct:
            new_state = max(new_state, BreakerState.RESTRICTED, key=lambda s: _STATE_SEVERITY[s])
            reasons.append(f"Daily loss {daily_loss_pct:.2f}% >= restricted threshold {self.thresholds.daily_loss_restricted_pct}%")
        elif daily_loss_pct >= self.thresholds.daily_loss_warning_pct:
            new_state = max(new_state, BreakerState.WARNING, key=lambda s: _STATE_SEVERITY[s])
            reasons.append(f"Daily loss {daily_loss_pct:.2f}% >= warning threshold {self.thresholds.daily_loss_warning_pct}%")

        # --- Check Total Drawdown ---
        if total_dd_pct >= self.thresholds.total_dd_kill_pct:
            new_state = BreakerState.KILL_SWITCH
            reasons.append(f"Total DD {total_dd_pct:.2f}% >= kill threshold {self.thresholds.total_dd_kill_pct}%")
        elif total_dd_pct >= self.thresholds.total_dd_restricted_pct:
            new_state = max(new_state, BreakerState.RESTRICTED, key=lambda s: _STATE_SEVERITY[s])
            reasons.append(f"Total DD {total_dd_pct:.2f}% >= restricted threshold {self.thresholds.total_dd_restricted_pct}%")
        elif total_dd_pct >= self.thresholds.total_dd_warning_pct:
            new_state = max(new_state, BreakerState.WARNING, key=lambda s: _STATE_SEVERITY[s])
            reasons.append(f"Total DD {total_dd_pct:.2f}% >= warning threshold {self.thresholds.total_dd_warning_pct}%")

        # --- Check Consecutive Losses ---
        if consecutive_losses >= self.thresholds.consecutive_loss_kill:
            new_state = BreakerState.KILL_SWITCH
            reasons.append(f"Consecutive losses {consecutive_losses} >= kill threshold {self.thresholds.consecutive_loss_kill}")
        elif consecutive_losses >= self.thresholds.consecutive_loss_restricted:
            new_state = max(new_state, BreakerState.RESTRICTED, key=lambda s: _STATE_SEVERITY[s])
            reasons.append(f"Consecutive losses {consecutive_losses} >= restricted threshold {self.thresholds.consecutive_loss_restricted}")
        elif consecutive_losses >= self.thresholds.consecutive_loss_warning:
            new_state = max(new_state, BreakerState.WARNING, key=lambda s: _STATE_SEVERITY[s])
            reasons.append(f"Consecutive losses {consecutive_losses} >= warning threshold {self.thresholds.consecutive_loss_warning}")

        # --- Check Health Score ---
        if health_score <= self.thresholds.health_kill:
            new_state = BreakerState.KILL_SWITCH
            reasons.append(f"Health score {health_score:.1f} <= kill threshold {self.thresholds.health_kill}")
        elif health_score <= self.thresholds.health_restricted:
            new_state = max(new_state, BreakerState.RESTRICTED, key=lambda s: _STATE_SEVERITY[s])
            reasons.append(f"Health score {health_score:.1f} <= restricted threshold {self.thresholds.health_restricted}")
        elif health_score <= self.thresholds.health_warning:
            new_state = max(new_state, BreakerState.WARNING, key=lambda s: _STATE_SEVERITY[s])
            reasons.append(f"Health score {health_score:.1f} <= warning threshold {self.thresholds.health_warning}")

        # Only escalate, never auto-downgrade
        if _STATE_SEVERITY[new_state] > _STATE_SEVERITY[self._state]:
            self._state = new_state
            self._reason = "; ".join(reasons) if reasons else ""
            self._details = reasons
            self._triggered_at = datetime.now(timezone.utc)
            self._save_persistent_state()

        return self._build_snapshot(daily_loss_pct, total_dd_pct, consecutive_losses, health_score)

    def _build_snapshot(
        self,
        daily_loss_pct: float,
        total_dd_pct: float,
        consecutive_losses: int,
        health_score: float,
    ) -> BreakerSnapshot:
        """Build immutable snapshot based on current state."""
        allowed = self._state in (BreakerState.NORMAL, BreakerState.WARNING)
        
        multiplier = 1.0
        if self._state == BreakerState.WARNING:
            multiplier = 0.75
        elif self._state == BreakerState.RESTRICTED:
            multiplier = 0.25
        elif self._state == BreakerState.KILL_SWITCH:
            multiplier = 0.0

        return BreakerSnapshot(
            state=self._state,
            triggered_at=self._triggered_at.isoformat() if self._triggered_at else None,
            reason=self._reason,
            daily_loss_pct=daily_loss_pct,
            total_dd_pct=total_dd_pct,
            consecutive_losses=consecutive_losses,
            health_score=health_score,
            allowed_to_trade=allowed,
            max_risk_multiplier=multiplier,
            details=self._details,
        )

    def manual_reset(self, admin_confirmed: bool = False) -> BreakerSnapshot:
        """
        Reset breaker to NORMAL. Requires explicit admin confirmation.
        This is the ONLY way to de-escalate from KILL_SWITCH.
        """
        if not admin_confirmed:
            raise PermissionError("Circuit breaker reset requires admin_confirmed=True")

        self._state = BreakerState.NORMAL
        self._reason = "Manual reset by admin"
        self._triggered_at = None
        self._details = ["Breaker manually reset to NORMAL"]
        self._save_persistent_state()

        return self._build_snapshot(0.0, 0.0, 0, 100.0)

    def force_kill(self, reason: str = "Manual kill switch activated") -> BreakerSnapshot:
        """Immediately activate KILL_SWITCH. Used for emergency."""
        self._state = BreakerState.KILL_SWITCH
        self._reason = reason
        self._triggered_at = datetime.now(timezone.utc)
        self._details = [reason]
        self._save_persistent_state()
        return self._build_snapshot(0.0, 0.0, 0, 0.0)
