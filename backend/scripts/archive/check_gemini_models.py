import asyncio
import httpx
from app.core.config import settings

async def list_models():
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        print("[ERROR] GEMINI_API_KEY is not set in .env")
        return

    print(f"Checking supported models for your API key...")
    
    for version in ["v1beta", "v1"]:
        url = f"https://generativelanguage.googleapis.com/{version}/models?key={api_key}"
        async with httpx.AsyncClient() as client:
            res = await client.get(url)
            print(f"\n--- API Version: {version} (Status {res.status_code}) ---")
            if res.status_code == 200:
                models = res.json().get("models", [])
                supported = []
                for m in models:
                    methods = m.get("supportedGenerationMethods", [])
                    if "generateContent" in methods:
                        name = m.get("name", "").replace("models/", "")
                        supported.append(name)
                print(f"Supported 'generateContent' models ({len(supported)} found):")
                for s in supported:
                    print(f"  -> {s}")
            else:
                print(f"Failed: {res.text}")

if __name__ == "__main__":
    asyncio.run(list_models())
