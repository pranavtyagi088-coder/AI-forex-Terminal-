import sys
try:
    from app.main import app
    print("\n============================================================")
    print(" [SUCCESS] app.main imported with ZERO errors!")
    print(f" [OK] App Name: {app.title} v{app.version}")
    print("============================================================\n")
except Exception as e:
    import traceback
    print("\n[ERROR IMPORTING APP]:")
    traceback.print_exc()
    sys.exit(1)
