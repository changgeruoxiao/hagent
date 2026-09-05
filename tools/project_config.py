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
VIA_DIAMETER, VIA_DRILL = 0.40, 0.20
EDGE_CLEARANCE = 0.30

# Layer intent. In1 is a hard invariant: GND only, nothing else, ever.
# In2 is the +3V3 plane plus an approved whitelist of low-speed GPIO nets
# (experiment B in doc/本地Agent后续执行计划_20260905.md §6): they may cross
# In2 because F/B-only routing left them unrouted. Critical nets stay off In2.
PLANE_POLICY = {
    'In1.Cu': {'GND'},
    'In2.Cu': {'+3V3'},
}
IN2_FORBIDDEN = {
    'USB_DM', 'USB_DP', 'USB_DM_P', 'USB_DP_P',
    'PA13', 'PA14', 'PB3',
    'OSC_IN', 'OSC_OUT', 'OSC32_IN', 'OSC32_OUT',
    'BOOT0', 'NRST', 'VCAP', 'VDDA', 'VREF+', 'VBAT',
}
SIGNAL_LAYERS = ('F.Cu', 'B.Cu')

REVISION = '1.1'
