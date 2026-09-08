from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
import numpy as np

from app.engines.market.regime import MarketRegimeDetector, MarketRegimeType, MarketRegimeResult
from app.engines.market.volume_profile import VolumeProfileEngine, VolumeProfileResult
from app.engines.structure.structure_engine import MarketStructureEngine


class ConfluenceGrade(str, Enum):
    A_PLUS_INSTITUTIONAL = "A_PLUS_INSTITUTIONAL"  # 80-100
    B_ACCEPTABLE = "B_ACCEPTABLE"                  # 65-79
    C_SUB_OPTIMAL = "C_SUB_OPTIMAL"                # 50-64
    REJECT_NO_CONFLUENCE = "REJECT_NO_CONFLUENCE"  # < 50


@dataclass
class TimeframeEvidence:
    timeframe: str
    regime: MarketRegimeType
    structure_bias: str
    has_bos: bool
    has_choch: bool
    weight: float


@dataclass
class ConfluenceScoreResult:
    total_confluence_score: float
    confluence_grade: ConfluenceGrade
    proposed_direction: str
    is_aligned_with_htf: bool
    value_area_location_score: float
    structure_alignment_score: float
    regime_alignment_score: float
    timeframe_breakdown: List[TimeframeEvidence]
    positive_confluences: List[str]
    negative_frictions: List[str]


class ConfluenceScoringEngine:
    """
    Institutional Multi-Timeframe & Confluence Scoring Engine (P2-#34 & #35).
    Computes mathematical confluence across HTF trend, SMC market structure, and Volume Profile.
    """

    TF_WEIGHTS = {
        "1D": 0.40,
        "4H": 0.30,
        "1H": 0.20,
        "15M": 0.10,
    }

    @classmethod
    def evaluate_confluence(
        cls,
        timeframe_candles: Dict[str, List[Dict[str, Any]]],
        proposed_direction: str = "BUY",
        current_price: Optional[float] = None,
        symbol: str = "EURUSD",
    ) -> ConfluenceScoreResult:
        dir_upper = proposed_direction.upper()
        timeframe_evidence: List[TimeframeEvidence] = []
        positive_factors: List[str] = []
        negative_factors: List[str] = []

        regime_weighted_score = 0.0
        structure_weighted_score = 0.0
        total_weight_applied = 0.0

        htf_alignments = []

        for tf, candles in timeframe_candles.items():
            if not candles or len(candles) < 15:
                continue

            weight = cls.TF_WEIGHTS.get(tf.upper(), 0.15)
            total_weight_applied += weight

            regime_res = MarketRegimeDetector.classify_regime(candles, symbol=symbol)
            struct_res = MarketStructureEngine.analyze_structure(candles)

            s_bias = struct_res.get("structure_bias", "NEUTRAL")
            has_bos = bool(struct_res.get("bos_detected", False))
            has_choch = bool(struct_res.get("choch_detected", False))

            timeframe_evidence.append(TimeframeEvidence(
                timeframe=tf,
                regime=regime_res.regime,
                structure_bias=s_bias,
                has_bos=has_bos,
                has_choch=has_choch,
                weight=weight,
            ))

            # Regime alignment check
            if dir_upper == "BUY":
                if regime_res.regime == MarketRegimeType.TRENDING_BULLISH_EXPANSION:
                    regime_weighted_score += 100.0 * weight
                    positive_factors.append(f"[{tf}] Bullish trending expansion aligned.")
                elif regime_res.regime == MarketRegimeType.RANGING_COMPRESSION:
                    regime_weighted_score += 60.0 * weight
                else:
                    regime_weighted_score += 10.0 * weight
                    negative_factors.append(f"[{tf}] Regime oppositional: {regime_res.regime.value}.")
            else:
                if regime_res.regime == MarketRegimeType.TRENDING_BEARISH_EXPANSION:
                    regime_weighted_score += 100.0 * weight
                    positive_factors.append(f"[{tf}] Bearish trending expansion aligned.")
                elif regime_res.regime == MarketRegimeType.RANGING_COMPRESSION:
                    regime_weighted_score += 60.0 * weight
                else:
                    regime_weighted_score += 10.0 * weight
                    negative_factors.append(f"[{tf}] Regime oppositional: {regime_res.regime.value}.")

            # Structure alignment check
            if (dir_upper == "BUY" and "BULLISH" in s_bias) or (dir_upper == "SELL" and "BEARISH" in s_bias):
                structure_weighted_score += 100.0 * weight
                if has_bos:
                    structure_weighted_score = min(100.0 * weight, structure_weighted_score + 10.0 * weight)
                    positive_factors.append(f"[{tf}] Break of Structure (BOS) in trade direction.")
            elif s_bias == "NEUTRAL":
                structure_weighted_score += 50.0 * weight
            else:
                structure_weighted_score += 10.0 * weight
                negative_factors.append(f"[{tf}] Market structure opposite to proposed direction ({s_bias}).")

            # HTF alignment: aligned if either structure or regime matches direction and not opposite
            if tf.upper() in ("1D", "4H"):
                is_htf_match = (
                    (dir_upper == "BUY" and ("BULLISH" in s_bias or regime_res.regime == MarketRegimeType.TRENDING_BULLISH_EXPANSION))
                    or (dir_upper == "SELL" and ("BEARISH" in s_bias or regime_res.regime == MarketRegimeType.TRENDING_BEARISH_EXPANSION))
                )
                htf_alignments.append(is_htf_match)

        if total_weight_applied > 0:
            final_regime_score = regime_weighted_score / total_weight_applied
            final_structure_score = structure_weighted_score / total_weight_applied
        else:
            final_regime_score = 50.0
            final_structure_score = 50.0

        # Volume Profile Value Area Location Scoring
        va_score = 65.0
        primary_tf_candles = timeframe_candles.get("1H") or timeframe_candles.get("1h") or (list(timeframe_candles.values())[0] if timeframe_candles else [])
        if primary_tf_candles and len(primary_tf_candles) >= 10:
            vp = VolumeProfileEngine.compute_profile(primary_tf_candles)
            check_price = current_price or float(primary_tf_candles[-1].get("close", 0))

            if check_price > 0 and vp.vah_price > vp.val_price:
                if dir_upper == "BUY":
                    if check_price <= vp.val_price:
                        va_score = 95.0
                        positive_factors.append(f"Discount Entry: Price at or below Value Area Low ({vp.val_price:.5f}).")
                    elif check_price <= vp.poc_price:
                        va_score = 80.0
                        positive_factors.append(f"Value Entry: Price below Point of Control ({vp.poc_price:.5f}).")
                    elif check_price >= vp.vah_price:
                        va_score = 30.0
                        negative_factors.append(f"Premium Friction: Buying at Value Area High ({vp.vah_price:.5f}).")
                else:
                    if check_price >= vp.vah_price:
                        va_score = 95.0
                        positive_factors.append(f"Premium Entry: Price at or above Value Area High ({vp.vah_price:.5f}).")
                    elif check_price >= vp.poc_price:
                        va_score = 80.0
                        positive_factors.append(f"Value Entry: Price above Point of Control ({vp.poc_price:.5f}).")
                    elif check_price <= vp.val_price:
                        va_score = 30.0
                        negative_factors.append(f"Discount Friction: Selling at Value Area Low ({vp.val_price:.5f}).")

        # Aggregate Confluence Formula: 40% Structure + 35% Regime + 25% Value Area
        aggregate_score = (final_structure_score * 0.40) + (final_regime_score * 0.35) + (va_score * 0.25)
        aggregate_score = round(max(0.0, min(100.0, aggregate_score)), 1)

        is_htf_aligned = all(htf_alignments) if htf_alignments else True

        if aggregate_score >= 80.0:
            grade = ConfluenceGrade.A_PLUS_INSTITUTIONAL
        elif aggregate_score >= 65.0:
            grade = ConfluenceGrade.B_ACCEPTABLE
        elif aggregate_score >= 50.0:
            grade = ConfluenceGrade.C_SUB_OPTIMAL
        else:
            grade = ConfluenceGrade.REJECT_NO_CONFLUENCE

        return ConfluenceScoreResult(
            total_confluence_score=aggregate_score,
            confluence_grade=grade,
            proposed_direction=dir_upper,
            is_aligned_with_htf=is_htf_aligned,
            value_area_location_score=round(va_score, 1),
            structure_alignment_score=round(final_structure_score, 1),
            regime_alignment_score=round(final_regime_score, 1),
            timeframe_breakdown=timeframe_evidence,
            positive_confluences=positive_factors,
            negative_frictions=negative_factors,
        )
