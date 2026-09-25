#!/usr/bin/env python3
"""Generate the first reviewable H743 V1 schematic stage.

This stage contains the MCU, minimum power, clocks, reset, boot selection and
external SWD/SWO connector. Ethernet and USB PHY circuits are intentionally
left for their component-reference review stages.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
V1 = Path(__file__).resolve().parent
TOOLS = REPO / "tools"
OUT = V1 / "kicad" / "h743_dev_v1.kicad_sch"
PRO = V1 / "kicad" / "h743_dev_v1.kicad_pro"
SYMLIB = V1 / "kicad" / "hagent.kicad_sym"
SYMTABLE = V1 / "kicad" / "sym-lib-table"

sys.path.insert(0, str(TOOLS))

from sch_build import SchBuilder, LibCache  # noqa: E402


MCU_LIB = "hagent:STM32H743ZITx"
MCU_FP = "Package_QFP:LQFP-144_20x20mm_P0.5mm"
FP_R = "Resistor_SMD:R_0603_1608Metric"
FP_C = "Capacitor_SMD:C_0402_1005Metric"
FP_C0603 = "Capacitor_SMD:C_0603_1608Metric"
FP_C0805 = "Capacitor_SMD:C_0805_2012Metric"
FP_C1206 = "Capacitor_SMD:C_1206_3216Metric"
FP_FB = "Inductor_SMD:L_0603_1608Metric"
FP_DIODE = "Diode_SMD:D_SMA"
FP_L = "Inductor_SMD:L_Bourns_SRP7028A_7.3x6.6mm"
FP_DCDC = "Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.29x3mm"
FP_CRYSTAL = "Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm"
FP_HEADER_3 = "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical"
FP_HEADER_6 = "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical"
FP_TP = "TestPoint:TestPoint_Pad_D1.0mm"

# TI's TPS54331 is not present in the KiCad system symbol library. This symbol
# follows the DDA package pinout from the TI datasheet and the legacy generator;
# the circuit values below are taken from TI's 3.3 V application example.
TPS54331_BLOCK = '''(symbol "TPS54331DDA"
    (pin_names (offset 1.016))
    (in_bom yes) (on_board yes)
    (property "Reference" "U" (at 0 13.97 0) (effects (font (size 1.27 1.27))))
    (property "Value" "TPS54331DDA" (at 0 -13.97 0) (effects (font (size 1.27 1.27))))
    (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
    (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
    (symbol "TPS54331DDA_0_1"
        (rectangle (start -7.62 11.43) (end 7.62 -11.43)
            (stroke (width 0.254) (type default)) (fill (type background)))
    )
    (symbol "TPS54331DDA_1_1"
        (pin output line (at -12.7 7.62 0) (length 5.08)
            (name "BOOT" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at -12.7 2.54 0) (length 5.08)
            (name "VIN" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin input line (at -12.7 -2.54 0) (length 5.08)
            (name "EN" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
        (pin input line (at -12.7 -7.62 0) (length 5.08)
            (name "SS" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
        (pin input line (at 12.7 7.62 180) (length 5.08)
            (name "VSENSE" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
        (pin output line (at 12.7 2.54 180) (length 5.08)
            (name "COMP" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 12.7 -2.54 180) (length 5.08)
            (name "GND" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))
        (pin output line (at 12.7 -7.62 180) (length 5.08)
            (name "PH" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -16.51 90) (length 5.08)
            (name "EP" (effects (font (size 1.27 1.27)))) (number "9" (effects (font (size 1.27 1.27)))))
    )
)'''

PIN_NET = {
    # Ethernet RMII (reserved now; Ethernet circuit is a later stage)
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
    # Debug and clocks
    "PA13": "SWDIO",
    "PA14": "SWCLK",
    "PB3": "SWO",
    "PH0": "HSE_IN",
    "PH1": "HSE_OUT",
    "PC14": "LSE_IN",
    "PC15": "LSE_OUT",
}

POWER_NETS = ("GND", "+3V3", "+5V")


def snap_grid(value: float) -> float:
    """Snap symbol origins to KiCad's 1.27 mm connection grid."""
    return round(round(float(value) / 1.27) * 1.27, 4)


def place_symbol(b, lib_id, ref, value, footprint, x, y, **kwargs):
    return b.place(lib_id, ref, value, footprint, snap_grid(x), snap_grid(y), **kwargs)


def mcu_symbol_block() -> str:
    """Return a local MCU symbol with the required shared VCAP net ERC-safe.

    AN4938 and MB1364 tie VCAP1 and VCAP2 together. KiCad's standard symbol
    marks both as power outputs, which creates a false ERC short on that
    required connection. This project-local symbol changes only the two pin
    electrical types to passive; package numbers and geometry remain intact.
    """
    block = LibCache.load("MCU_ST_STM32H7:STM32H743ZITx").block_text
    block = block.replace(
        '(symbol "MCU_ST_STM32H7:STM32H743ZITx"',
        '(symbol "STM32H743ZITx"',
        1,
    )
    for number in ("71", "106"):
        token = f'(number "{number}"'
        end = block.index(token) + len(token)
        start = block.rfind("(pin ", 0, end)
        type_start = start + len("(pin ")
        type_end = block.find(" ", type_start)
        if start < 0 or type_end < 0 or "VCAP" not in block[start:end]:
            raise RuntimeError(f"Could not identify VCAP pin {number} in STM32H743 symbol")
        block = block[:type_start] + "passive" + block[type_end:]
    return block


def net_for_pin(name: str) -> str:
    if name in PIN_NET:
        return PIN_NET[name]
    if name == "VCAP":
        return "VCAP"
    if name in ("VDD", "VDD33_USB"):
        return "+3V3"
    if name in ("VSS", "VSSA"):
        return "GND"
    return {
        "VDDA": "VDDA",
        "VREF+": "VREF+",
        "VBAT": "VBAT",
        "PDR_ON": "PDR_ON",
        "NRST": "NRST",
        "BOOT0": "BOOT0",
    }.get(name, name)


def connect(b: SchBuilder, inst, pin: str, net: str, length=3.81) -> None:
    if net in POWER_NETS:
        b.pin_power(inst, pin, net, length)
    else:
        b.pin_label(inst, pin, net, length)


def two_pin(b, lib_id, ref, value, footprint, x, y, net1, net2, angle=0,
            datasheet="~", dnp=False):
    inst = place_symbol(b, lib_id, ref, value, footprint, x, y, angle=angle,
                        datasheet=datasheet, dnp=dnp)
    connect(b, inst, "1", net1)
    connect(b, inst, "2", net2)
    return inst


def rc(b, ref, value, footprint, x, y, net_top, net_bottom, angle=0, dnp=False):
    lib_id = "Device:C" if ref.startswith("C") else "Device:R"
    return two_pin(b, lib_id, ref, value, footprint, x, y, net_top, net_bottom,
                   angle=angle, dnp=dnp)


def add_power_stage(b: SchBuilder) -> None:
    b.note("POWER INPUT / 5V TO 3V3 REGULATOR (PROVISIONAL)", 25, 20, 2.0)
    b.note("TPS54331 values start from TI SLVS839H 3.3V example; confirm source/load/thermal budget before layout.",
           25, 27, 1.35)

    # Temporary 5 V source connector. Pin/header part and footprint stay open
    # until the board input and mechanical positions are frozen.
    j1 = place_symbol(b, "Connector_Generic:Conn_01x02", "J1", "5V_INPUT_TBD", "", 42, 78)
    connect(b, j1, "1", "+5V")
    connect(b, j1, "2", "GND")
    b.flag(*j1.pin_pos("1"))
    b.flag(*j1.pin_pos("2"))

    u2 = place_symbol(
        b, "hagent:TPS54331DDA", "U2", "TPS54331DDAR", FP_DCDC, 135, 90,
        custom_block=TPS54331_BLOCK,
        datasheet="https://www.ti.com/lit/ds/symlink/tps54331.pdf",
        val_off=(0, 18.5),
    )
    for pin, net in {
        "1": "BOOT", "2": "+5V", "3": "+5V", "4": "SS", "5": "FB",
        "6": "COMP", "7": "GND", "8": "PH", "9": "GND",
    }.items():
        connect(b, u2, pin, net)

    # TPS54331 input and control components.
    rc(b, "C22", "100nF", FP_C0603, 76, 57, "+5V", "GND")
    rc(b, "C23", "10uF", FP_C0805, 91, 57, "+5V", "GND")
    rc(b, "C24", "10uF", FP_C0805, 106, 57, "+5V", "GND")
    rc(b, "C25", "100nF", FP_C0603, 178, 74, "BOOT", "PH")
    rc(b, "C26", "10nF", FP_C0603, 104, 119, "SS", "GND")

    # The DDA version has a thermal pad; it is grounded per TI's datasheet.
    d1 = two_pin(b, "Device:D_Schottky", "D1", "B340A", FP_DIODE,
                 170, 105, "PH", "GND", datasheet="https://www.diodes.com/assets/Datasheets/ds13007.pdf")
    l1 = two_pin(b, "Device:L", "L1", "6.8uH / Isat>=4A", FP_L,
                 197, 105, "PH", "3V3_SW", angle=90)
    r1 = two_pin(b, "Device:R", "R1", "0R", FP_R, 231, 105, "3V3_SW", "+3V3", angle=90)
    b.flag(*r1.pin_pos("2"))
    rc(b, "C27", "47uF", FP_C1206, 219, 78, "3V3_SW", "GND")
    rc(b, "C28", "47uF", FP_C1206, 235, 78, "3V3_SW", "GND")

    # Feedback divider is sized for approximately 3.3 V from the 0.8 V reference.
    rc(b, "R2", "10.2k", FP_R, 249, 66, "3V3_SW", "FB")
    rc(b, "R3", "3.24k", FP_R, 264, 66, "FB", "GND")
    rc(b, "R4", "29.4k", FP_R, 178, 145, "COMP", "COMP_M", angle=90)
    rc(b, "C29", "1nF", FP_C0603, 201, 145, "COMP_M", "GND")
    rc(b, "C30", "47pF", FP_C, 216, 145, "COMP", "GND")


def add_mcu_and_decoupling(b: SchBuilder, mcu_block: str) -> None:
    b.note("MCU CORE — STM32H743ZIT6 / LQFP144", 280, 20, 2.0)
    b.note("11 x 100nF: one local bypass capacitor per VDD pin; VDD33_USB has separate local bypass.",
           370, 218, 1.35)
    lib = b.lib(MCU_LIB, mcu_block)
    available_pin_names = {p.name for p in lib.pins}
    missing_reserved = sorted(set(PIN_NET) - available_pin_names)
    if missing_reserved:
        b.note(
            "PACKAGE BLOCKER: reserved digital pin(s) absent from this symbol/package: "
            + ", ".join(missing_reserved) + "; see OPEN_ISSUES.md.",
            280, 32, 1.25,
        )
    u1 = place_symbol(
        b, MCU_LIB, "U1", "STM32H743ZIT6", MCU_FP, 320, 200,
        custom_block=mcu_block,
        datasheet="https://www.st.com/resource/en/datasheet/stm32h743zi.pdf",
    )

    pins = {int(p.number): p for p in lib.pins}
    drawn = {}
    for num in sorted(pins):
        p = pins[num]
        net = net_for_pin(p.name)
        pos = tuple(round(v, 2) for v in u1.pin_pos(str(num)))
        if pos in drawn:
            if drawn[pos] != net:
                raise RuntimeError(f"Conflicting nets on stacked pin coordinate {pos}: {drawn[pos]} vs {net}")
            continue
        if re.fullmatch(r"P[A-K]\d+(_C)?", p.name) and p.name not in PIN_NET:
            drawn[pos] = "__NO_CONNECT__"
            b.no_connect(*pos)
            continue
        drawn[pos] = net
        connect(b, u1, str(num), net)

    # Count the 11 VDD pins in the selected LQFP144 library symbol so the
    # schematic bypass count stays synchronized with the package.
    vdd_count = sum(1 for p in pins.values() if p.name == "VDD")
    if vdd_count != 11:
        raise RuntimeError(f"Expected 11 VDD pins on STM32H743ZIT6 LQFP144, found {vdd_count}")

    # Main MCU VDD decoupling: 100 nF at every VDD pin plus one bulk capacitor.
    x_positions = [390, 420, 450, 480]
    y_positions = [242, 262, 282]
    for i in range(11):
        x = x_positions[i % len(x_positions)]
        y = y_positions[i // len(x_positions)]
        rc(b, f"C{i + 1}", "100nF", FP_C, x, y, "+3V3", "GND")
    rc(b, "C12", "4.7uF", FP_C0603, 510, 262, "+3V3", "GND")

    # Both VCAP pins share the VCAP net and get one 2.2 uF low-ESR capacitor each.
    rc(b, "C13", "2.2uF", FP_C0603, 390, 326, "VCAP", "GND")
    rc(b, "C14", "2.2uF", FP_C0603, 415, 326, "VCAP", "GND")

    # Analog rail, reference, USB transceiver rail, and backup supply.
    fb1 = two_pin(b, "Device:FerriteBead", "FB1", "600R@100MHz", FP_FB,
                  453, 326, "+3V3", "VDDA")
    b.flag(*fb1.pin_pos("2"))
    rc(b, "C15", "1uF", FP_C0603, 475, 326, "VDDA", "GND")
    rc(b, "C16", "100nF", FP_C, 496, 326, "VDDA", "GND")
    rc(b, "R5", "0R", FP_R, 518, 326, "VDDA", "VREF+")
    rc(b, "C17", "1uF", FP_C0603, 540, 326, "VREF+", "GND")
    rc(b, "C18", "100nF", FP_C, 562, 326, "VREF+", "GND")
    rc(b, "C19", "1uF", FP_C0603, 475, 358, "+3V3", "GND")
    rc(b, "C20", "100nF", FP_C, 496, 358, "+3V3", "GND")
    r6 = rc(b, "R6", "0R", FP_R, 518, 358, "+3V3", "VBAT")
    b.flag(*r6.pin_pos("2"))
    rc(b, "C21", "100nF", FP_C, 540, 358, "VBAT", "GND")
    rc(b, "R7", "10k", FP_R, 562, 358, "+3V3", "PDR_ON")


def add_clocks_reset_debug(b: SchBuilder) -> None:
    b.note("CLOCKS — crystal values preliminary; verify exact crystal datasheets and board parasitics.",
           25, 203, 1.4)
    # Frequencies and nominal crystal load capacitance are cross-checks from
    # the WeAct H7 reference. Load capacitor values are preliminary estimates.
    two_pin(b, "Device:Crystal", "X1", "25MHz CL=10pF (TBD)", FP_CRYSTAL,
            88, 235, "HSE_IN", "HSE_OUT")
    rc(b, "C31", "15pF (prelim)", FP_C, 70, 255, "HSE_IN", "GND")
    rc(b, "C32", "15pF (prelim)", FP_C, 107, 255, "HSE_OUT", "GND")
    two_pin(b, "Device:Crystal", "X2", "32.768kHz CL=7pF (TBD)", FP_CRYSTAL,
            88, 296, "LSE_IN", "LSE_OUT")
    rc(b, "C33", "10pF (prelim)", FP_C, 70, 316, "LSE_IN", "GND")
    rc(b, "C34", "10pF (prelim)", FP_C, 107, 316, "LSE_OUT", "GND")

    b.note("RESET / BOOT / SWD + SWO", 165, 203, 1.7)
    rc(b, "R8", "10k", FP_R, 178, 238, "+3V3", "NRST")
    rc(b, "C35", "100nF", FP_C, 196, 238, "NRST", "GND")
    two_pin(b, "Switch:SW_Push", "SW1", "RESET", "Button_Switch_THT:SW_PUSH_6mm",
            221, 238, "NRST", "GND")

    rc(b, "R9", "10k", FP_R, 178, 294, "BOOT0", "GND")
    j2 = place_symbol(b, "Connector_Generic:Conn_01x03", "J2", "BOOT0_SELECT", FP_HEADER_3, 222, 294)
    for pin, net in {"1": "+3V3", "2": "BOOT0", "3": "GND"}.items():
        connect(b, j2, pin, net)
    b.note("J2: fit jumper 1-2 only for system boot; remove for normal boot (BOOT0 pulled low).",
           167, 307, 1.2)

    j3 = place_symbol(b, "Connector_Generic:Conn_01x06", "J3", "SWD_SWO", FP_HEADER_6, 260, 280)
    for pin, net in {
        "1": "+3V3", "2": "SWDIO", "3": "SWCLK", "4": "SWO", "5": "NRST", "6": "GND",
    }.items():
        connect(b, j3, pin, net)
    b.note("J3 pinout: 1=3V3, 2=SWDIO, 3=SWCLK, 4=SWO, 5=NRST, 6=GND.",
           230, 304, 1.2)


def add_testpoints_and_scope_notes(b: SchBuilder) -> None:
    for ref, value, net, x, y in [
        ("TP1", "+3V3", "+3V3", 525, 232),
        ("TP2", "+5V", "+5V", 555, 232),
        ("TP3", "VCAP", "VCAP", 525, 254),
        ("TP4", "NRST", "NRST", 555, 254),
        ("TP5", "BOOT0", "BOOT0", 525, 276),
    ]:
        tp = place_symbol(b, "Connector:TestPoint", ref, value, FP_TP, x, y)
        connect(b, tp, "1", net)

    b.note("NEXT: USB_FS Device, ULPI/USB2-HS Host, LAN8742A Ethernet, and GPIO headers after part review.",
           25, 380, 1.45)
    b.note("Phase 1 schematic only. PCB placement/routing and fabrication checks are not complete.",
           25, 397, 1.35)


def build(mcu_block: str) -> SchBuilder:
    b = SchBuilder(
        "H743 Dev V1 — MCU core, power, clocks, reset and debug",
        paper="A2",
        project="h743_dev_v1",
    )
    add_power_stage(b)
    add_mcu_and_decoupling(b, mcu_block)
    add_clocks_reset_debug(b)
    add_testpoints_and_scope_notes(b)
    return b


def main() -> int:
    bad = [p for p in PIN_NET if not re.fullmatch(r"P[A-K]\d+", p)]
    if bad:
        raise SystemExit(f"Invalid GPIO names in frozen map: {bad}")
    if len(PIN_NET.values()) != len(set(PIN_NET.values())):
        raise SystemExit("Duplicate schematic net in frozen pin reservation map")
    if PIN_NET["PB13"] != "USB_HS_ULPI_D6" or PIN_NET["PG14"] != "ETH_TXD1":
        raise SystemExit("Frozen PB13/PG14 architecture mapping changed")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    mcu_block = mcu_symbol_block()
    b = build(mcu_block)
    b.write(OUT)
    SYMLIB.write_text(
        '(kicad_symbol_lib (version 20231120) (generator "kicad_symbol_editor")\n'
        + mcu_block + "\n" + TPS54331_BLOCK + "\n)\n",
        encoding="utf-8",
    )
    SYMTABLE.write_text(
        '(sym_lib_table (version 7)\n'
        '  (lib (name "hagent") (type "KiCad") (uri "${KIPRJMOD}/hagent.kicad_sym") '
        '(options "") (descr "H743 V1 project-local symbols"))\n'
        ')\n',
        encoding="utf-8",
    )
    if not PRO.exists():
        PRO.write_text(json.dumps({"meta": {"filename": "h743_dev_v1", "version": 1}}, indent=2) + "\n",
                       encoding="utf-8")
    print(f"Generated: {OUT}")
    print(f"Project:   {PRO}")
    print(f"Symbols: {len(b.symbols)}, wires: {len(b.wires)}, labels: {len(b.labels)}, power flags: {len(b.flags)}")
    available = {p.name for p in LibCache.load("MCU_ST_STM32H7:STM32H743ZITx").pins}
    missing = sorted(set(PIN_NET) - available)
    if missing:
        print(f"ARCHITECTURE BLOCKER: package does not expose reserved pins: {', '.join(missing)}")
    print("NOTE: first implementation stage only; Ethernet, USB PHYs, connectors and PCB remain open.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
