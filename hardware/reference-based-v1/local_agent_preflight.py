#!/usr/bin/env python3
"""Local-agent preflight for H743 reference-based V1.

Runs architecture guards and checks whether a usable KiCad CLI is available.
No third-party Python packages are required.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V1 = Path(__file__).resolve().parent
KICAD_DIR = V1 / "kicad"


def run_py(path: Path) -> bool:
    print(f"\n==> {path.name}")
    proc = subprocess.run([sys.executable, str(path)], cwd=ROOT)
    return proc.returncode == 0


def find_kicad_cli() -> str | None:
    env = os.environ.get("KICAD_CLI")
    if env and Path(env).exists():
        return env

    found = shutil.which("kicad-cli")
    if found:
        return found

    if os.name == "nt":
        candidates = [
            Path(r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"),
            Path(r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe"),
            Path(r"C:\Program Files\KiCad\8.0\bin\kicad-cli.exe"),
        ]
        for p in candidates:
            if p.exists():
                return str(p)
    return None


def main() -> int:
    print("H743 reference-based-v1 local preflight")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Repo:   {ROOT}")
    print(f"V1:     {V1}")

    ok = True
    ok &= run_py(V1 / "check_pin_reservations.py")
    ok &= run_py(V1 / "validate_manifest.py")

    KICAD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nPASS: KiCad workspace exists: {KICAD_DIR}")

    cli = find_kicad_cli()
    if not cli:
        print("\nWARN: kicad-cli not found.")
        print("Install KiCad or set KICAD_CLI to the full kicad-cli executable path.")
        ok = False
    else:
        print(f"\nPASS: kicad-cli = {cli}")
        proc = subprocess.run(
            [cli, "--version"],
            text=True,
            capture_output=True,
        )
        version = (proc.stdout or proc.stderr).strip()
        print(f"KiCad CLI version: {version or 'unknown'}")
        if proc.returncode != 0:
            ok = False

    sch = KICAD_DIR / "h743_dev_v1.kicad_sch"
    pcb = KICAD_DIR / "h743_dev_v1.kicad_pcb"

    print("\nArtifacts:")
    print(f"  schematic: {'FOUND' if sch.exists() else 'not generated yet'}")
    print(f"  pcb:       {'FOUND' if pcb.exists() else 'not created yet'}")

    if ok:
        print("\nPRE-FLIGHT PASS")
        return 0

    print("\nPRE-FLIGHT INCOMPLETE")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
