#!/usr/bin/env python3
"""
ParkSafe — one-click launcher.

Double-click `start_parksafe.command` (Mac), `start_parksafe.bat` (Windows),
or `start_parksafe.sh` (Linux) — they all just run this script.

What it does, in order:
  1. Compiles the C++ safety engine (engine-cpp/safety_engine)      [g++]
  2. Compiles & starts the Java municipal service on port 8081       [javac/java]
  3. Seeds the SQLite demo data (only if the DB doesn't exist yet)   [python3]
  4. Trains the ML scoring model (only if not already trained)      [python3]
  5. Starts the FastAPI backend on port 8000                        [uvicorn]
  6. Opens index.html in your default browser

Everything keeps running in this window — close it (or Ctrl+C) to stop
Python and Java. If a required tool (g++/java/python3) is missing, this
script tells you what to install and keeps going where it can.
"""
import os
import subprocess
import sys
import time
import webbrowser
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
CPP_DIR = os.path.join(ROOT, "engine-cpp")
JAVA_DIR = os.path.join(ROOT, "service-java")
PY_DIR = os.path.join(ROOT, "backend-python")
SCRIPTS_DIR = os.path.join(ROOT, "scripts")

PYTHON = sys.executable or "python3"
processes = []


def banner(msg):
    print("\n" + "=" * 60)
    print(msg)
    print("=" * 60)


def have(cmd):
    return shutil.which(cmd) is not None


def run(cmd, cwd=None, check=True):
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    if check and result.returncode != 0:
        raise SystemExit(f"Command failed: {' '.join(cmd)}")
    return result


def start_background(cmd, cwd=None, logfile=None):
    print(f"$ {' '.join(cmd)}  (background)")
    log = open(logfile, "w") if logfile else subprocess.DEVNULL
    proc = subprocess.Popen(cmd, cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
    processes.append(proc)
    return proc


def main():
    banner("ParkSafe — starting the full stack (C++ + Java + Python)")

    # ---------------------------------------------------------- 1. C++ ---
    engine_bin = os.path.join(CPP_DIR, "safety_engine")
    if have("g++"):
        if not os.path.isfile(engine_bin):
            banner("Building C++ safety engine")
            run(["make"], cwd=CPP_DIR)
        else:
            print("C++ engine already built — skipping.")
    else:
        print("⚠ g++ not found — skipping C++ engine build.")
        print("  The Python API will still work using its pure-Python fallback scorer.")
        print("  Install a C++ compiler (e.g. `sudo apt install g++`) for the full stack.")

    # --------------------------------------------------------- 2. Java ---
    class_file = os.path.join(JAVA_DIR, "ChallanService.class")
    if have("javac") and have("java"):
        if not os.path.isfile(class_file):
            banner("Compiling Java municipal service")
            run(["javac", "ChallanService.java"], cwd=JAVA_DIR)
        else:
            print("Java service already compiled — skipping.")
        banner("Starting Java municipal service on port 8081")
        start_background(["java", "ChallanService", "8081"], cwd=JAVA_DIR,
                          logfile=os.path.join(ROOT, "java_service.log"))
        time.sleep(1.5)
    else:
        print("⚠ javac/java not found — skipping the municipal microservice.")
        print("  Admin features (tow-zones, challans) won't work without a JDK 17+.")

    # ------------------------------------------------------- 3. Python ---
    if not have(PYTHON):
        raise SystemExit("python3 not found — please install Python 3.10+ and try again.")

    db_path = os.path.join(PY_DIR, "parksafe.db")
    if not os.path.isfile(db_path):
        banner("Seeding demo data")
        run([PYTHON, os.path.join(SCRIPTS_DIR, "seed_db.py")], cwd=ROOT)
    else:
        print("Database already seeded — skipping.")

    model_path = os.path.join(ROOT, "models", "safety_model.joblib")
    if not os.path.isfile(model_path):
        banner("Training ML scoring model (scikit-learn)")
        try:
            run([PYTHON, os.path.join(SCRIPTS_DIR, "train_model.py")], cwd=ROOT)
        except SystemExit:
            print("⚠ Could not train the ML model (missing scikit-learn?). "
                  "The C++/rule-based engine will still work.")
    else:
        print("ML model already trained — skipping.")

    banner("Starting Python API (FastAPI) on port 8000")
    try:
        import uvicorn  # noqa: F401
    except ImportError:
        print("Installing backend dependencies (first run only)...")
        run([PYTHON, "-m", "pip", "install", "-r", "requirements.txt",
             "--break-system-packages"], cwd=PY_DIR, check=False)

    start_background([PYTHON, "-m", "uvicorn", "app:app", "--port", "8000"], cwd=PY_DIR,
                      logfile=os.path.join(ROOT, "python_api.log"))
    time.sleep(2.5)

    # -------------------------------------------------------- 4. Open ---
    index_path = os.path.join(ROOT, "index.html")
    banner("Opening ParkSafe in your browser")
    print(f"Frontend:      {index_path}")
    print("Python API:    http://localhost:8000  (docs at /docs)")
    print("Java service:  http://localhost:8081/health")
    print("\nIn the app, click the gear icon next to your profile and choose")
    print('"Use ParkSafe API (localhost:8000)" to switch from demo data to the live stack.')
    webbrowser.open(f"file://{index_path}")

    print("\nAll set! Keep this window open — closing it stops the backend.")
    print("Press Ctrl+C to stop everything.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        banner("Shutting down...")
        for p in processes:
            p.terminate()


if __name__ == "__main__":
    main()
