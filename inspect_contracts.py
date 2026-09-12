from pathlib import Path

ROOT = Path(r"C:\Users\PRANAV TYAGI\PycharmProjects\WelcomeScreen")

def inspect_file(path_str, start_line=1, max_lines=100):
    p = ROOT / path_str
    if not p.exists():
        print(f"[{path_str} NOT FOUND]")
        return
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    print(f"\n{'='*30} {path_str} (Lines {start_line}-{min(len(lines), start_line+max_lines)}) {'='*30}")
    for idx in range(start_line - 1, min(len(lines), start_line + max_lines - 1)):
        print(f"{idx+1:4d} | {lines[idx]}")

# 1. Inspect broker routes & response models in trades.py
inspect_file("backend/app/api/routes/trades.py", 160, 60)

# 2. Inspect frontend api.ts
inspect_file("frontend/src/lib/api.ts", 80, 70)

# 3. Inspect frontend useCockpitStore.ts
inspect_file("frontend/src/store/useCockpitStore.ts", 1, 80)
