"""Shared paths and fabrication rules; no commands run at import time.

This module is the machine-readable source for board geometry and fabrication limits.
Generators/checkers should import these values instead of repeating literals.
"""
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
DRC = OUT / 'drc.json'

BOARD_W, BOARD_H = 85.0, 65.0
CLEARANCE, SIGNAL_WIDTH = 0.15, 0.20
POWER_WIDTH = 0.50
GND_TRACE_WIDTH = 0.25
VIA_DIAMETER, VIA_DRILL = 0.40, 0.20
EDGE_CLEARANCE = 0.30

# Layer intent.
# In1 is a hard invariant: GND only, nothing else, ever.
# In2 experiment B is +3V3 plane plus an explicit class of ordinary, unaliased
# GPIO nets. Functional/critical nets are fail-closed: unless a net is listed as
# an ordinary GPIO here, it stays on F/B. If a GPIO later gains a high-speed role,
# give it a semantic net name or explicitly remove it from this set.
PLANE_POLICY = {
    'In1.Cu': {'GND'},
    'In2.Cu': {'+3V3'},
}

# Current project names ordinary exported GPIO nets by MCU pin name. Only these
# raw GPIO-style names are eligible for experiment-B In2 routing. SWD pins are
# excluded explicitly; USB/clock nets already use semantic names and therefore
# never enter this set.
IN2_ALLOWED_SIGNAL_NETS = {
    f'P{port}{pin}'
    for port in 'ABCDEFGHIK'
    for pin in range(16)
}
IN2_ALLOWED_SIGNAL_NETS.update({'PC2_C', 'PC3_C'})
IN2_ALLOWED_SIGNAL_NETS.difference_update({'PA13', 'PA14', 'PB3'})

SIGNAL_LAYERS = ('F.Cu', 'B.Cu')

REVISION = '1.1'
