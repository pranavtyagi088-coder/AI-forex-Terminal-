from pathlib import Path
ROOT = Path(r"C:\Users\PRANAV TYAGI\PycharmProjects\WelcomeScreen")

trades_py = ROOT / "backend/app/api/routes/trades.py"
text = trades_py.read_text(encoding="utf-8-sig", errors="replace")

print("=== /proposals/{proposal_id}/approve ENDPOINT ===")
lines = text.splitlines()
for idx, line in enumerate(lines):
    if "/proposals/{proposal_id}/approve" in line:
        for j in range(idx, min(len(lines), idx + 65)):
            print(f"{j+1:4d} | {lines[j]}")
        break
