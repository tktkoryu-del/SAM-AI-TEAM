#!/usr/bin/env python3
"""Run deterministic repository-level acceptance checks for SAM AI TEAM."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main() -> int:
    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode:
        print("\nACCEPTANCE_GATE=FAIL")
        return completed.returncode
    print("\nACCEPTANCE_GATE=PASS (source checks only; runtime/cloud acceptance still requires live evidence)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
