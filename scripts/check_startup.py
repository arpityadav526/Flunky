"""Warm launcher budget. CI tolerates loaded shared runners; Mac target is 150ms."""

import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

executable = Path(sys.executable).with_name("flunky.exe" if os.name == "nt" else "flunky")
timings = []
for index in range(12):
    started = time.perf_counter()
    subprocess.run([str(executable), "--help"], check=True, stdout=subprocess.DEVNULL)
    if index >= 2:
        timings.append(time.perf_counter() - started)
budget = float(os.environ.get("FLUNKY_STARTUP_BUDGET", "0.5" if os.environ.get("CI") else "0.15"))
median = statistics.median(timings)
print(f"Warm help median: {median * 1000:.1f}ms; budget: {budget * 1000:.0f}ms")
if median > budget:
    raise SystemExit(1)
