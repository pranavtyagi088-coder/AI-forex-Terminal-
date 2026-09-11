from pathlib import Path

ROOT = Path(r"C:\Users\PRANAV TYAGI\PycharmProjects\WelcomeScreen")
admin_file = ROOT / "backend" / "app" / "api" / "routes" / "admin.py"

if admin_file.exists():
    print(admin_file.read_text(encoding="utf-8"))
else:
    print("admin.py not found")
