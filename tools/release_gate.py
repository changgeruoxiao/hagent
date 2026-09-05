#!/usr/bin/env python3
"""Prototype release gate.

This is intentionally stricter than KiCad DRC alone. It verifies that the
checked-in/intermediate artifacts are fresh enough for the current build and
then executes the independent semantic gates.

Run after schematic/netlist/PCB/routing/DRC generation and before fab export.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from project_config import DRC, NET, PCB, SCH, WS  # noqa: E402


def fail(msg: str) -> None:
    print(f"✗ release gate: {msg}")
    raise SystemExit(2)


def require_fresh(child: Path, parents: tuple[Path, ...], label: str) -> None:
    if not child.exists():
        fail(f"missing {child}")
    missing = [p for p in parents if not p.exists()]
    if missing:
        fail(f"{label}: missing parents: {', '.join(map(str, missing))}")
    newest_parent = max(p.stat().st_mtime_ns for p in parents)
    if child.stat().st_mtime_ns < newest_parent:
        fail(f"{label}: stale artifact {child.name}; regenerate from current sources")


def run_gate(script: str) -> None:
    cmd = [sys.executable, str(WS / "tools" / script)]
    print("gate:", " ".join(cmd))
    rc = subprocess.run(cmd, cwd=str(WS)).returncode
    if rc:
        fail(f"{script} failed with exit {rc}")


def check_drc_errors() -> None:
    data = json.loads(DRC.read_text(encoding="utf-8"))
    violations = [x for x in data.get("violations", []) if x.get("severity") == "error"]
    unconnected = [x for x in data.get("unconnected_items", []) if x.get("severity") == "error"]
    if violations or unconnected:
        fail(f"KiCad DRC not clean: {len(violations)} errors, {len(unconnected)} unconnected")
    print("✓ KiCad DRC: 0 error / 0 unconnected")


def main() -> int:
    # Artifact lineage: a PCB build must never silently consume an older .net;
    # parity/DRC must describe the current PCB + schematic pair.
    require_fresh(NET, (SCH,), "schematic -> netlist")
    require_fresh(DRC, (SCH, PCB), "schematic+PCB -> DRC/parity report")

    run_gate("check_netlist.py")
    run_gate("check_layer_policy.py")
    check_drc_errors()
    run_gate("check_schematic_parity.py")

    print("✓ RELEASE GATE PASS: artifacts are eligible for prototype fab export")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
