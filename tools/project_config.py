"""Shared paths and fabrication rules; no commands run at import time."""
import os
import shutil
from pathlib import Path

WS = Path(__file__).resolve().parents[1]


def _find_kicad_root() -> Path:
    """Return a KiCad install root containing share/kicad.

    Priority:
      1. KICAD_ROOT environment variable
      2. kicad-cli from PATH
      3. common Windows per-user / Program Files installs
      4. common Linux roots (/usr, /usr/local)
    """
    env = os.environ.get("KICAD_ROOT")
    if env:
        return Path(env).expanduser().resolve()

    cli = shutil.which("kicad-cli")
    if cli:
        p = Path(cli).resolve()
        # Windows: <root>/bin/kicad-cli.exe
        # Linux:   /usr/bin/kicad-cli -> root /usr
        if p.parent.name.lower() == "bin":
            return p.parent.parent

    candidates = []

    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates += [
            Path(local) / "Programs/KiCad/10.0",
            Path(local) / "Programs/KiCad/9.0",
            Path(local) / "Programs/KiCad/8.0",
        ]

    program_files = os.environ.get("ProgramFiles") or os.environ.get("PROGRAMFILES")
    if program_files:
        candidates += [
            Path(program_files) / "KiCad/10.0",
            Path(program_files) / "KiCad/9.0",
            Path(program_files) / "KiCad/8.0",
        ]

    candidates += [Path("/usr"), Path("/usr/local")]

    for root in candidates:
        if (root / "share/kicad/symbols").exists():
            return root.resolve()

    # Keep a deterministic path for diagnostics rather than crashing on import.
    if local:
        return (Path(local) / "Programs/KiCad/10.0").resolve()
    return Path("/usr").resolve()


KICAD_ROOT = _find_kicad_root()
KI = KICAD_ROOT / "bin"
SYMBOLS = KICAD_ROOT / "share/kicad/symbols"
FOOTPRINTS = KICAD_ROOT / "share/kicad/footprints"

OUT = Path(os.environ.get("HAGENT_OUTPUT", str(WS / "kicad"))).resolve()
STEM = "stm32h743_core"
PCB = OUT / (STEM + ".kicad_pcb")
SCH = OUT / (STEM + ".kicad_sch")
NET = OUT / (STEM + ".net")
DSN = OUT / (STEM + ".dsn")
SES = OUT / (STEM + ".ses")

BOARD_W, BOARD_H = 85.0, 65.0
CLEARANCE, SIGNAL_WIDTH = 0.15, 0.20
VIA_DIAMETER, VIA_DRILL = 0.60, 0.30
EDGE_CLEARANCE = 0.30
REVISION = "1.1"
