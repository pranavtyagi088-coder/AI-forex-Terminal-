import logging
from typing import Dict, Any, Optional
from app.core.config import settings
from app.services.ai.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)

class ChartAnalyzer:
    """
    Multi-provider Analysis Engine:
    1. Gemini (PRIMARY)
    2. OpenAI (OPTIONAL FALLBACK)
    3. Deterministic Safety Gate (Guaranteed zero crash)
    """

    def __init__(self):
        self.gemini = GeminiProvider()
        self.openai_key = settings.OPENAI_API_KEY

    def _get_analysis_prompt(self, market_context: Optional[Dict[str, Any]] = None) -> str:
        ctx_str = f"Market Context: {market_context}" if market_context else "Standard forex technical analysis."
        return f"""
You are an institutional Forex technical analyst and risk manager.
Analyze the provided chart and context:
{ctx_str}

Return STRICT JSON only matching this schema:
{{
  "summary": "Concise summary of institutional market structure and price action",
  "trend": "BULLISH" | "BEARISH" | "SIDEWAYS" | "VOLATILE_CHOP",
  "trend_direction": "BULLISH" | "BEARISH" | "SIDEWAYS" | "VOLATILE_CHOP",
  "bias": "LONG" | "SHORT" | "NEUTRAL" | "NO_TRADE",
  "confidence": 0.85,
  "support_levels": [1.0820, 1.0800],
  "resistance_levels": [1.0880, 1.0910],
  "key_patterns": ["Key pattern name"],
  "market_regime": "TRENDING" | "RANGING" | "BREAKOUT" | "CHOPPY",
  "why_reasons": ["Reason 1", "Reason 2"],
  "invalidation_level": 1.0790,
  "no_trade_warning": false
}}
"""

    def _normalize_result(self, res: Dict[str, Any], provider: str) -> Dict[str, Any]:
        if not isinstance(res, dict):
            res = {}
        
        trend = res.get("trend") or res.get("trend_direction") or "SIDEWAYS"
        bias = res.get("bias") or ("LONG" if trend == "BULLISH" else "SHORT" if trend == "BEARISH" else "NEUTRAL")
        confidence = float(res.get("confidence", 0.85) or 0.85)
        
        if confidence > 1.0 and confidence <= 100.0:
            confidence = confidence / 100.0

        return {
            "summary": res.get("summary") or f"Market analysis indicates {trend} bias with {confidence:.0%} confidence.",
            "trend": trend,
            "trend_direction": trend,
            "bias": bias,
            "confidence": confidence,
            "support_levels": res.get("support_levels", []),
            "resistance_levels": res.get("resistance_levels", []),
            "key_patterns": res.get("key_patterns", ["Institutional Technical Structure"]),
            "market_regime": res.get("market_regime", "TRENDING" if trend in ("BULLISH", "BEARISH") else "RANGING"),
            "why_reasons": res.get("why_reasons", [f"Price action aligned with {trend} market state."]),
            "invalidation_level": res.get("invalidation_level"),
            "no_trade_warning": bool(res.get("no_trade_warning", False)),
            "provider_used": provider
        }

    def _deterministic_fallback(self, market_context: Optional[Dict[str, Any]] = None, reason: str = "AI Offline") -> Dict[str, Any]:
        logger.warning(f"Safety Gate: Using deterministic fallback ({reason})")
        current_price = 1.0
        if market_context and "current_price" in market_context:
            try:
                current_price = float(market_context["current_price"])
            except Exception:
                pass

        return self._normalize_result({
            "summary": f"Deterministic safety fallback baseline generated ({reason}).",
            "trend": "SIDEWAYS",
            "trend_direction": "SIDEWAYS",
            "bias": "NEUTRAL",
            "confidence": 0.85,
            "support_levels": [round(current_price * 0.995, 5)],
            "resistance_levels": [round(current_price * 1.005, 5)],
            "key_patterns": ["Baseline deterministic rule"],
            "market_regime": "RANGING",
            "why_reasons": [
                f"AI service fallback triggered ({reason}).",
                "Deterministic baseline generated safely.",
                "Adhere to risk management rules."
            ],
            "invalidation_level": None,
            "no_trade_warning": True
        }, provider="deterministic_fallback")

    async def _try_openai_fallback(self, prompt: str, base64_image: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if not self.openai_key:
            return None
        try:
            import httpx, json
            headers = {
                "Authorization": f"Bearer {self.openai_key}",
                "Content-Type": "application/json"
            }
            messages = [{"role": "user", "content": []}]
            if base64_image:
                img_url = base64_image if base64_image.startswith("data:") else f"data:image/png;base64,{base64_image}"
                messages[0]["content"].append({"type": "image_url", "image_url": {"url": img_url}})
            messages[0]["content"].append({"type": "text", "text": prompt})

            payload = {
                "model": settings.OPENAI_MODEL,
                "messages": messages,
                "response_format": {"type": "json_object"},
                "temperature": 0.2
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                if res.status_code == 200:
                    parsed = json.loads(res.json()["choices"][0]["message"]["content"])
                    return self._normalize_result(parsed, provider="openai_fallback")
        except Exception as e:
            logger.warning(f"OpenAI fallback error: {type(e).__name__}")
        return None

    async def analyze(
        self,
        base64_image: Optional[str] = None,
        market_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        prompt = self._get_analysis_prompt(market_context)

        # 1. PRIMARY: Gemini
        if self.gemini.is_configured():
            try:
                result = await self.gemini.analyze_chart(
                    prompt=prompt,
                    base64_image=base64_image
                )
                return self._normalize_result(result, provider=f"gemini ({self.gemini.model})")
            except Exception as e:
                logger.warning(f"Primary Gemini provider failed ({type(e).__name__}). Trying fallback...")

        # 2. SECONDARY: OpenAI
        openai_result = await self._try_openai_fallback(prompt, base64_image)
        if openai_result:
            return openai_result

        # 3. TERTIARY: Safe Deterministic Fallback
        return self._deterministic_fallback(market_context, reason="All AI providers unavailable or unconfigured")
