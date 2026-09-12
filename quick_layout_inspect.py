from pathlib import Path
ROOT = Path(r"C:\Users\PRANAV TYAGI\PycharmProjects\WelcomeScreen")

def inspect_lines(path_str, start_keyword, lines_count=40):
    p = ROOT / path_str
    if not p.exists():
        print(f"[{path_str} NOT FOUND]")
        return
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if start_keyword in line:
            print(f"\n--- {path_str} (around '{start_keyword}') ---")
            for i in range(max(0, idx - 5), min(len(lines), idx + lines_count)):
                print(f"{i+1:4d} | {lines[i]}")
            return

inspect_lines("frontend/src/App.tsx", "return (", 50)
inspect_lines("frontend/src/components/cockpit/ZoneRadarPanel.tsx", "export function", 25)
