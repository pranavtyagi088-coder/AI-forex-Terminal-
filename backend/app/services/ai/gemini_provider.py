import asyncio
import json
import logging
from typing import Dict, Any, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class GeminiProvider:
    """
    Direct REST API provider for Google Gemini via httpx.AsyncClient.
    Features:
    - Secure x-goog-api-key header (Zero secret leakage in URLs/logs)
    - Automatic retry with exponential backoff on transient 503 / 429 / 500 errors
    """
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        raw_model = model or settings.GEMINI_MODEL or "gemini-3.6-flash"
        self.model = raw_model.removeprefix("models/")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 0)

    async def analyze_chart(
        self,
        prompt: str,
        base64_image: Optional[str] = None,
        mime_type: str = "image/png",
        timeout_seconds: float = 30.0,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        if not self.is_configured():
            raise ValueError("GEMINI_API_KEY is not configured in environment.")

        endpoint = f"{self.base_url}/{self.model}:generateContent"
        
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        parts = []
        if base64_image:
            clean_base64 = base64_image.split(",")[-1] if "," in base64_image else base64_image
            parts.append({
                "inline_data": {
                    "mime_type": mime_type,
                    "data": clean_base64
                }
            })
        
        parts.append({"text": prompt})

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": parts
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "response_mime_type": "application/json"
            }
        }

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            last_err = None
            for attempt in range(1, max_retries + 1):
                try:
                    response = await client.post(
                        endpoint,
                        json=payload,
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        candidates = data.get("candidates", [])
                        if not candidates:
                            raise RuntimeError("Gemini returned empty candidate list.")

                        raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
                        try:
                            return json.loads(raw_text)
                        except json.JSONDecodeError:
                            cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                            return json.loads(cleaned)

                    # Transient Error Handling (503 / 429 / 500) -> Retry with backoff
                    if response.status_code in (503, 429, 500, 502, 504) and attempt < max_retries:
                        backoff = attempt * 1.5
                        logger.warning(f"Gemini API transient HTTP {response.status_code}. Retrying in {backoff}s (Attempt {attempt}/{max_retries})...")
                        await asyncio.sleep(backoff)
                        continue

                    try:
                        err_detail = response.json().get("error", {}).get("message", response.text)
                    except Exception:
                        err_detail = f"HTTP {response.status_code}"
                    
                    logger.error(f"Gemini API returned status {response.status_code}")
                    raise RuntimeError(f"Gemini API returned status {response.status_code}: {err_detail}")

                except httpx.TimeoutException:
                    if attempt < max_retries:
                        await asyncio.sleep(1.0)
                        continue
                    raise TimeoutError("Gemini API request timed out.")
                except Exception as e:
                    last_err = e
                    if attempt < max_retries and "503" in str(e):
                        await asyncio.sleep(1.5)
                        continue
                    raise last_err
