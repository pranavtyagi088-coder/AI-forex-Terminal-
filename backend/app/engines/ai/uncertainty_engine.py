from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class UncertaintyLevel(str, Enum):
    LOW = "LOW"                                       # Confidence >= 80%, Zero conflict
    MODERATE = "MODERATE"                             # Confidence 65-79%
    HIGH = "HIGH"                                     # Confidence < 65% or Low image quality
    CRITICAL_HALLUCINATION_SUSPECT = "CRITICAL_HALLUCINATION_SUSPECT"  # AI directly contradicts deterministic math


class AISidecarAnalysis(BaseModel):
    bias: str = Field(..., pattern="^(BULLISH|BEARISH|NEUTRAL)$")
    confidence: float = Field(..., ge=0.0, le=100.0)
    detected_patterns: List[str] = Field(default_factory=list)
    key_levels_identified: List[float] = Field(default_factory=list)
    reasoning_summary: str = ""
    is_advisory_only: bool = True  # Golden Rule #8: AI is SIDECAR, not authority


class UncertaintyEvaluationResult(BaseModel):
    uncertainty_level: UncertaintyLevel
    calibrated_confidence: float  # Adjusted confidence after calibration
    effective_ai_weight: float    # 0.0 to 0.15 max (Strictly clamped)
    is_usable_as_evidence: bool
    hallucination_detected: bool
    contradiction_flags: List[str] = Field(default_factory=list)
    sidecar_advisory_notes: List[str] = Field(default_factory=list)


class AIUncertaintyGuard:
    """
    Institutional AI Vision Uncertainty & Hallucination Guard (P2-#36 & #38).
    Enforces Golden Rule #8: AI is SIDECAR, not authority.
    Guarantees that AI hallucinations or conflicts with deterministic math are neutralized instantly.
    """

    MAX_AI_EVIDENCE_WEIGHT = 0.15  # AI can never contribute more than 15% to any decision

    @classmethod
    def evaluate_ai_evidence(
        cls,
        ai_analysis: Optional[AISidecarAnalysis],
        deterministic_structure_bias: str = "NEUTRAL",
        deterministic_regime: str = "RANGING_COMPRESSION",
        image_validation_passed: bool = True,
    ) -> UncertaintyEvaluationResult:
        if not ai_analysis or not image_validation_passed:
            return UncertaintyEvaluationResult(
                uncertainty_level=UncertaintyLevel.HIGH,
                calibrated_confidence=0.0,
                effective_ai_weight=0.0,
                is_usable_as_evidence=False,
                hallucination_detected=False,
                contradiction_flags=["NO_AI_DATA_OR_INVALID_IMAGE"],
                sidecar_advisory_notes=["AI Vision analysis unavailable or image payload failed security check."],
            )

        raw_conf = ai_analysis.confidence
        ai_bias = ai_analysis.bias.upper()
        struct_bias = deterministic_structure_bias.upper()
        regime = deterministic_regime.upper()

        contradictions = []
        notes = []
        hallucination_detected = False

        # ── 1. Conflict & Contradiction Detection (Math > AI) ──
        if ai_bias == "BULLISH" and "BEARISH" in struct_bias:
            contradictions.append(f"AI hallucination suspect: AI claims BULLISH but deterministic structure is {struct_bias}.")
            hallucination_detected = True
        elif ai_bias == "BEARISH" and "BULLISH" in struct_bias:
            contradictions.append(f"AI hallucination suspect: AI claims BEARISH but deterministic structure is {struct_bias}.")
            hallucination_detected = True

        if ai_bias != "NEUTRAL" and "CHOPPY" in regime:
            contradictions.append(f"AI claims directional bias in verified CHOPPY market regime ({regime}).")

        # ── 2. Confidence Calibration & Clamping ──
        if hallucination_detected:
            calibrated_conf = round(raw_conf * 0.1, 1)  # Punish hallucination
            uncertainty = UncertaintyLevel.CRITICAL_HALLUCINATION_SUSPECT
            effective_weight = 0.0
            usable = False
            notes.append("CRITICAL: AI output contradicts deterministic ground truth. AI evidence discarded.")
        elif raw_conf < 65.0:
            calibrated_conf = round(raw_conf * 0.8, 1)
            uncertainty = UncertaintyLevel.HIGH
            effective_weight = 0.0
            usable = False
            notes.append("AI confidence below institutional threshold (65%). Ignored.")
        elif raw_conf < 80.0:
            calibrated_conf = round(raw_conf * 0.9, 1)
            uncertainty = UncertaintyLevel.MODERATE
            effective_weight = round(cls.MAX_AI_EVIDENCE_WEIGHT * 0.5, 3)
            usable = True
            notes.append("Moderate AI confidence. Low sidecar weight applied.")
        else:
            calibrated_conf = round(raw_conf * 0.95, 1)
            uncertainty = UncertaintyLevel.LOW
            effective_weight = cls.MAX_AI_EVIDENCE_WEIGHT
            usable = True
            notes.append("High AI confidence aligned with market conditions.")

        return UncertaintyEvaluationResult(
            uncertainty_level=uncertainty,
            calibrated_confidence=calibrated_conf,
            effective_ai_weight=effective_weight,
            is_usable_as_evidence=usable,
            hallucination_detected=hallucination_detected,
            contradiction_flags=contradictions,
            sidecar_advisory_notes=notes,
        )
