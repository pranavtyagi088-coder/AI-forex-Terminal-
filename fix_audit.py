from pathlib import Path
ROOT = Path(r"C:\Users\PRANAV TYAGI\PycharmProjects\WelcomeScreen")

print("=" * 70)
print(" FRONTEND SRC STRUCTURE")
print("=" * 70)
for sub in ["lib", "services", "store", "hooks", "components/cockpit"]:
    d = ROOT / "frontend/src" / sub
    if d.exists():
        print(f"\n[DIR] frontend/src/{sub}/")
        for f in sorted(d.glob("*")):
            if f.is_file():
                print(f"    {f.name}  ({f.stat().st_size / 1024:.1f} KB)")

# Show api.ts export signatures
print("\n" + "=" * 70)
print(" api.ts EXPORTS")
print("=" * 70)
for candidate in ["frontend/src/lib/api.ts", "frontend/src/services/api.ts"]:
    p = ROOT / candidate
    if p.exists():
        print(f"\n[FOUND] {candidate}")
        text = p.read_text(encoding="utf-8-sig", errors="replace")
        for idx, line in enumerate(text.splitlines()):
            s = line.strip()
            if s.startswith("export ") or "async function" in s or "function " in s:
                print(f"    L{idx+1}: {s[:110]}")

# Show cockpitStore.ts state slices
print("\n" + "=" * 70)
print(" cockpitStore.ts SLICES")
print("=" * 70)
for candidate in ["frontend/src/store/cockpitStore.ts", "frontend/src/store/useCockpitStore.ts"]:
    p = ROOT / candidate
    if p.exists():
        print(f"\n[FOUND] {candidate}")
        text = p.read_text(encoding="utf-8-sig", errors="replace")
        for idx, line in enumerate(text.splitlines()[:200]):
            s = line.strip()
            if s.startswith("interface ") or s.startswith("type ") or s.startswith("export ") or s.startswith("const use"):
                print(f"    L{idx+1}: {s[:120]}")
