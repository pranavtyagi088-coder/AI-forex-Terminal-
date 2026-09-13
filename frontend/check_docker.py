import subprocess

print("="*70)
print("🐳 CHECKING DOCKER & SYSTEM READINESS")
print("="*70)

# Check Docker CLI
try:
    res = subprocess.run(["docker", "--version"], capture_output=True, text=True)
    if res.returncode == 0:
        print(f"✅ Docker CLI Found: {res.stdout.strip()}")
    else:
        print("❌ Docker CLI not working properly.")
except FileNotFoundError:
    print("❌ Docker is NOT installed or NOT in system PATH.")

# Check Docker Daemon
try:
    res = subprocess.run(["docker", "info"], capture_output=True, text=True)
    if res.returncode == 0:
        print("🟢 Docker Daemon is RUNNING & HEALTHY!")
        docker_ready = True
    else:
        print("🟡 Docker is installed, but Docker Desktop is NOT RUNNING.")
        docker_ready = False
except Exception:
    docker_ready = False

print("="*70)
if docker_ready:
    print("\033[92;1m>>> READY FOR OPTION A (DOCKER PRODUCTION STAGING) <<<\033[0m")
else:
    print("\033[93;1m>>> DOCKER NOT RUNNING -> RECOMMEND OPTION C (ANALYTICS ENGINE) <<<\033[0m")
print("="*70)
