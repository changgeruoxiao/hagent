#!/usr/bin/env python3
"""Generate the MCU/pin-reservation scaffold for H743 reference-based V1.

This deliberately does NOT generate Ethernet PHY, USB PHY, power regulator,
connectors, or PCB layout. It creates a reviewable starting schematic whose
MCU pin assignments match DESIGN_MANIFEST.yaml/PINMAP.md.

Requires the same KiCad symbol-library environment used by tools/sch_build.py.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
V1 = Path(__file__).resolve().parent
TOOLS = REPO / "tools"
OUT = V1 / "kicad" / "h743_dev_v1.kicad_sch"

sys.path.insert(0, str(TOOLS))

from sch_build import SchBuilder, LibCache  # noqa: E402


MCU_LIB = "MCU_ST_STM32H7:STM32H743ZITx"
MCU_FP = "Package_QFP:LQFP-144_20x20mm_P0.5mm"

PIN_NET = {
    # Ethernet RMII
    "PA1": "ETH_REF_CLK",
    "PA2": "ETH_MDIO",
    "PC1": "ETH_MDC",
    "PA7": "ETH_CRS_DV",
    "PC4": "ETH_RXD0",
    "PC5": "ETH_RXD1",
    "PG11": "ETH_TX_EN",
    "PG13": "ETH_TXD0",
    "PG14": "ETH_TXD1",

    # USB FS
    "PA11": "USB_FS_DM",
    "PA12": "USB_FS_DP",
    "PA9": "USB_FS_VBUS",

    # USB HS / ULPI
    "PA3": "USB_HS_ULPI_D0",
    "PA5": "USB_HS_ULPI_CK",
    "PB0": "USB_HS_ULPI_D1",
    "PB1": "USB_HS_ULPI_D2",
    "PB10": "USB_HS_ULPI_D3",
    "PB11": "USB_HS_ULPI_D4",
    "PB12": "USB_HS_ULPI_D5",
    "PB13": "USB_HS_ULPI_D6",
    "PB5": "USB_HS_ULPI_D7",
    "PC0": "USB_HS_ULPI_STP",
    "PC2": "USB_HS_ULPI_DIR",
    "PC3": "USB_HS_ULPI_NXT",

    # Debug
    "PA13": "SWDIO",
    "PA14": "SWCLK",
    "PB3": "SWO",

    # Oscillators
    "PH0": "HSE_IN",
    "PH1": "HSE_OUT",
    "PC14": "LSE_IN",
    "PC15": "LSE_OUT",
}


def net_for_pin(name: str) -> str:
    if name in PIN_NET:
        return PIN_NET[name]
    if name == "VCAP":
        return "VCAP"
    if name in ("VDD", "VDD33_USB"):
        return "+3V3"
    if name in ("VSS", "VSSA"):
        return "GND"
    special = {
        "VDDA": "VDDA",
        "VREF+": "VREF+",
        "VBAT": "VBAT",
        "PDR_ON": "PDR_ON",
        "NRST": "NRST",
        "BOOT0": "BOOT0",
    }
    return special.get(name, name)


def connect(b: SchBuilder, inst, pin: str, net: str) -> None:
    if net in ("+3V3", "GND", "+5V"):
        b.pin_power(inst, pin, net, 3.81)
    else:
        b.pin_label(inst, pin, net, 3.81)


def build() -> SchBuilder:
    b = SchBuilder(
        "H743 Dev V1 - MCU scaffold",
        paper="A2",
        project="h743_dev_v1",
    )

    lib = LibCache.load(MCU_LIB)
    u1 = b.place(
        MCU_LIB,
        "U1",
        "STM32H743ZIT6",
        MCU_FP,
        270,
        180,
    )

    pins = {int(p.number): p for p in lib.pins}
    drawn = {}

    for num in sorted(pins):
        p = pins[num]
        net = net_for_pin(p.name)
        pos = tuple(round(v, 2) for v in u1.pin_pos(str(num)))
        if pos in drawn:
            if drawn[pos] != net:
                raise RuntimeError(
                    f"Conflicting nets on stacked symbol coordinate {pos}: "
                    f"{drawn[pos]} vs {net}"
                )
            continue
        drawn[pos] = net
        connect(b, u1, str(num), net)

    # Architecture guards.
    assert PIN_NET["PB13"] == "USB_HS_ULPI_D6"
    assert PIN_NET["PG14"] == "ETH_TXD1"
    assert len(PIN_NET.values()) == len(set(PIN_NET.values()))

    b.note("REFERENCE-BASED V1 MCU SCAFFOLD", 25, 20, 2.2)
    b.note("PB13 = ULPI_D6; Ethernet RMII_TXD1 = PG14", 25, 28, 1.5)
    b.note("USB FS: PA11/PA12; USB HS: external ULPI PHY", 25, 35, 1.5)
    b.note("Do not treat this scaffold as a complete/tape-out-ready schematic.", 25, 42, 1.5)

    # Add grouped notes so the local agent has obvious areas to extend.
    b.note("TODO: POWER / VCAP / VDDA / VREF / VBAT / PDR_ON", 25, 70, 1.5)
    b.note("TODO: CLOCK / RESET / BOOT / SWD", 25, 85, 1.5)
    b.note("TODO: USB FS USB-C DEVICE", 25, 100, 1.5)
    b.note("TODO: USB HS ULPI PHY + USB-A HOST VBUS SWITCH", 25, 115, 1.5)
    b.note("TODO: LAN8742A RMII + RJ45", 25, 130, 1.5)
    b.note("TODO: IO HEADERS after reserved-pin audit", 25, 145, 1.5)

    return b


def main() -> int:
    # Validate that all frozen names look like STM32 GPIO names.
    bad = [p for p in PIN_NET if not re.fullmatch(r"P[A-K]\d+", p)]
    if bad:
        raise SystemExit(f"Invalid GPIO names in frozen map: {bad}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    b = build()
    b.write(OUT)
    print(f"Generated: {OUT}")
    print(f"Symbols: {len(b.symbols)}, wires: {len(b.wires)}, labels: {len(b.labels)}")
    print("NOTE: scaffold only; peripheral circuits are intentionally not generated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
