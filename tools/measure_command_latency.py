"""Measure the latency of Night Light's user-facing command path.

This measures what a person actually waits for when they click the pinned moon
or open the controls: a short-lived command process starts, authenticates to the
resident app over the local endpoint, is acknowledged, and exits.

It is a command-roundtrip boundary, not an input-to-photon measurement. It does
not capture pointer-to-pixel latency, compositor time, or the moment a window
becomes visually complete. Do not describe results from this tool as "open time"
or as a perceptual claim.

The default command is --show, which opens the controls window and never changes
display output, so a measurement run cannot alter the user's screen. Pass
--command to measure another verb, understanding that verbs like --toggle do
change the display.

Usage:
    python tools/measure_command_latency.py --samples 10 --out results.json

Requires a resident app. Start one with:  NightLight.exe --background
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def default_executable() -> Path:
    local = os.environ.get("LOCALAPPDATA", "")
    return Path(local) / "Programs" / "Night Light" / "app" / "NightLight.exe"


def process_tree_memory(name: str = "NightLight") -> dict:
    """Working set of every matching process, via PowerShell so no dependency."""
    script = (
        f"Get-Process -Name '{name}*' -ErrorAction SilentlyContinue | "
        "Select-Object Id,ProcessName,WorkingSet64 | ConvertTo-Json -Compress"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, timeout=30,
    )
    raw = (result.stdout or "").strip()
    if not raw:
        return {"processes": [], "total_bytes": 0}
    parsed = json.loads(raw)
    if isinstance(parsed, dict):
        parsed = [parsed]
    return {
        "processes": [
            {"pid": p["Id"], "name": p["ProcessName"], "working_set_bytes": p["WorkingSet64"]}
            for p in parsed
        ],
        "total_bytes": sum(p["WorkingSet64"] for p in parsed),
    }


def sample(executable: Path, command: str, timeout: float) -> dict:
    """One command roundtrip, measured from spawn to process exit."""
    start = time.perf_counter()
    completed = subprocess.run(
        [str(executable), command],
        capture_output=True, text=True, timeout=timeout,
        creationflags=0x08000000,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return {
        "elapsed_ms": round(elapsed_ms, 3),
        "exit_code": completed.returncode,
        "stderr": (completed.stderr or "").strip()[:200],
    }


def percentile(values: list[float], fraction: float) -> float:
    """Nearest-rank percentile. With ten samples, p95 is the largest value."""
    if not values:
        raise ValueError("no samples")
    ordered = sorted(values)
    rank = max(1, min(len(ordered), int(-(-fraction * len(ordered) // 1))))
    return ordered[rank - 1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=10)
    parser.add_argument("--command", default="--show")
    parser.add_argument("--executable", type=Path, default=None)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--settle", type=float, default=1.0,
                        help="Seconds between samples, so each starts from rest.")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    executable = args.executable or default_executable()
    if not executable.exists():
        print(f"Night Light is not installed at {executable}", file=sys.stderr)
        return 2
    if args.samples < 1:
        print("--samples must be at least 1", file=sys.stderr)
        return 2

    before = process_tree_memory()
    if not before["processes"]:
        print("No resident Night Light process. Start one with --background first.", file=sys.stderr)
        return 2

    samples = []
    for index in range(args.samples):
        if index:
            time.sleep(args.settle)
        samples.append(sample(executable, args.command, args.timeout))

    after = process_tree_memory()
    failures = [s for s in samples if s["exit_code"] != 0]
    timings = [s["elapsed_ms"] for s in samples if s["exit_code"] == 0]

    report = {
        "schema": 1,
        "measured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "boundary": "command process spawn to exit, including local endpoint acknowledgement",
        "not_measured": [
            "input-to-photon latency",
            "time until the controls window is visually complete",
            "compositor and GPU present time",
        ],
        "executable": str(executable),
        "command": args.command,
        "samples": samples,
        "failures": len(failures),
        "memory": {
            "before": before,
            "after": after,
            "growth_bytes": after["total_bytes"] - before["total_bytes"],
        },
    }
    if timings:
        report["summary_ms"] = {
            "n": len(timings),
            "min": round(min(timings), 3),
            "median": round(statistics.median(timings), 3),
            "p95": round(percentile(timings, 0.95), 3),
            "max": round(max(timings), 3),
        }

    text = json.dumps(report, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    if timings:
        s = report["summary_ms"]
        print(f"n={s['n']} min={s['min']}ms median={s['median']}ms p95={s['p95']}ms max={s['max']}ms")
    print(f"failures={len(failures)} memory_growth_bytes={report['memory']['growth_bytes']}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
