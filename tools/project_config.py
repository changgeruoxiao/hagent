"""Shared paths and fabrication rules; no commands run at import time."""
import os
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
KICAD_ROOT = Path(os.environ.get("KICAD_ROOT", str(Path(os.environ['LOCALAPPDATA']) / 'Programs/KiCad/10.0')))
KI = KICAD_ROOT / 'bin'
SYMBOLS = KICAD_ROOT / 'share/kicad/symbols'
FOOTPRINTS = KICAD_ROOT / 'share/kicad/footprints'
OUT = Path(os.environ.get('HAGENT_OUTPUT', str(WS / 'kicad'))).resolve()
STEM = 'stm32h743_core'
PCB = OUT / (STEM + '.kicad_pcb')
SCH = OUT / (STEM + '.kicad_sch')
NET = OUT / (STEM + '.net')
DSN = OUT / (STEM + '.dsn')
SES = OUT / (STEM + '.ses')
BOARD_W, BOARD_H = 85.0, 65.0
CLEARANCE, SIGNAL_WIDTH = 0.15, 0.20
VIA_DIAMETER, VIA_DRILL = 0.60, 0.30
EDGE_CLEARANCE = 0.30
REVISION = '1.1'
