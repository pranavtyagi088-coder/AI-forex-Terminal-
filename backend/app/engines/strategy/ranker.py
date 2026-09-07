import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from app.models.strategy import Strategy
from app.engines.indicators.technical import TechnicalSnapshot
from app.services.news.news_engine import MacroContext
from app.services.social.base import SentimentResult

logger = logging.getLogger(__name__)

@dataclass
class StrategyScoreCard:
    strategy_id: int
    name: str
    evidence_grade: str
    final_score: int
    technical_fit: int
    volatility_fit: int
    news_fit: int
    social_fit: int
    reasons: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)

@dataclass
class StrategyRankingOutput:
    selected_pair: str
    best_strategy: Optional[StrategyScoreCard]
    alternative_strategies: List[StrategyScoreCard]
    evaluated_count: int

class StrategySelectionRanker:
    """Evaluates and ranks all strategies in the database against current live market intelligence"""

    def score_single_strategy(
        self,
        strat: Strategy,
        tech_snap: TechnicalSnapshot,
        macro: MacroContext,
        sentiment: SentimentResult,
        proposed_direction: str = "BUY"
    ) -> StrategyScoreCard:
        
        reasons = []
        risks = []
        
        # 1. Technical & Regime Fit (Max 40 pts)
        tech_fit = 20
        if tech_snap.trend_direction == proposed_direction:
            tech_fit += 10
            reasons.append(f"Trend ({tech_snap.trend_direction}) aligns with strategy direction ({proposed_direction})")
        else:
            risks.append(f"Trend ({tech_snap.trend_direction}) conflicts with proposed direction ({proposed_direction})")
            
        if tech_snap.structure_confirmed:
            tech_fit += 10
            reasons.append("Market structure (HH/HL or LH/LL) confirmed")
            
        # 2. Volatility Fit (Max 20 pts)
        vol_fit = 15
        if tech_snap.volatility_state == "NORMAL":
            vol_fit = 20
            reasons.append("Market volatility is NORMAL (optimal execution window)")
        elif tech_snap.volatility_state == "EXTREME":
            vol_fit = 5
            risks.append("Extreme market volatility detected")
            
        # 3. News Risk Sensitivity (Max 20 pts)
        news_fit = 20
        if macro.news_risk_level == "HIGH":
            news_fit = 10
            risks.append(f"High impact central bank releases detected ({macro.high_impact_news_count} events)")
        elif macro.news_risk_level == "EXTREME":
            news_fit = 0
            risks.append("Extreme news event imminent — strategy execution discouraged")
        else:
            reasons.append("Macro news risk is LOW")
            
        # 4. Social Sentiment Fit (Max 20 pts)
        social_fit = 10
        if sentiment.sentiment_label == proposed_direction:
            social_fit = 20
            reasons.append(f"Community sentiment is {sentiment.sentiment_label} (aligned)")
        elif sentiment.sentiment_label != "NEUTRAL" and sentiment.sentiment_label != proposed_direction:
            social_fit = 5
            risks.append(f"Social sentiment is {sentiment.sentiment_label} (conflicts with {proposed_direction})")

        total_score = tech_fit + vol_fit + news_fit + social_fit
        
        # Evidence Grade Cap
        grade = str(getattr(strat, "evidence_grade", "B")).upper()
        if grade == "B":
            total_score = min(total_score, 85)
        elif grade == "C":
            total_score = min(total_score, 60)
        elif grade == "D":
            total_score = min(total_score, 35)

        return StrategyScoreCard(
            strategy_id=getattr(strat, "id", 0),
            name=getattr(strat, "name", "Proprietary Strategy"),
            evidence_grade=grade,
            final_score=total_score,
            technical_fit=tech_fit,
            volatility_fit=vol_fit,
            news_fit=news_fit,
            social_fit=social_fit,
            reasons=reasons,
            risks=risks
        )

    def rank_strategies(
        self,
        pair: str,
        strategies: List[Strategy],
        tech_snap: TechnicalSnapshot,
        macro: MacroContext,
        sentiment: SentimentResult,
        proposed_direction: str = "BUY"
    ) -> StrategyRankingOutput:

        if not strategies:
            return StrategyRankingOutput(
                selected_pair=pair,
                best_strategy=None,
                alternative_strategies=[],
                evaluated_count=0
            )

        cards = [
            self.score_single_strategy(s, tech_snap, macro, sentiment, proposed_direction)
            for s in strategies
        ]

        cards.sort(key=lambda x: x.final_score, reverse=True)

        best = cards[0] if cards else None
        alternatives = cards[1:4] if len(cards) > 1 else []

        return StrategyRankingOutput(
            selected_pair=pair,
            best_strategy=best,
            alternative_strategies=alternatives,
            evaluated_count=len(cards)
        )
