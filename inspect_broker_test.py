from pathlib import Path

ROOT = Path(r"C:\Users\PRANAV TYAGI\PycharmProjects\WelcomeScreen")
bt_file = ROOT / "backend/tests/test_broker_api.py"

if bt_file.exists():
    text = bt_file.read_text(encoding="utf-8-sig", errors="replace")
    print("=== FIRST 45 LINES OF test_broker_api.py ===")
    for line in text.splitlines()[:45]:
        print(line)
