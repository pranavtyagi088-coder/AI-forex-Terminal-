from pathlib import Path

ROOT = Path(r"C:\Users\PRANAV TYAGI\PycharmProjects\WelcomeScreen")

def show(path_str):
    p = ROOT / path_str
    if p.exists():
        print(f"\n{'='*30} {path_str} {'='*30}")
        print(p.read_text(encoding="utf-8-sig", errors="replace"))

show("frontend/src/main.tsx")
show("frontend/src/App.tsx")
