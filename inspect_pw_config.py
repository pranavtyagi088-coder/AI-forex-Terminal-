from pathlib import Path

ROOT = Path(r"C:\Users\PRANAV TYAGI\PycharmProjects\WelcomeScreen")
p = ROOT / "frontend/playwright.config.ts"
if not p.exists():
    p = ROOT / "playwright.config.ts"

if p.exists():
    print(f"=== {p} ===")
    print(p.read_text(encoding="utf-8-sig", errors="replace"))
else:
    print("[playwright.config.ts NOT FOUND]")
