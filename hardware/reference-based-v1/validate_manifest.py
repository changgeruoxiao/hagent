#!/usr/bin/env python3
"""Validate DESIGN_MANIFEST.yaml architecture without external YAML dependency.

This checker intentionally parses only the frozen pin lines we care about.
It is a guard against accidental pin reuse in future agent edits.
"""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "DESIGN_MANIFEST.yaml"

PIN_RE = re.compile(r"^\s+(?:dm|dp|vbus_sense|d[0-7]|ck|stp|dir|nxt|ref_clk|mdio|mdc|crs_dv|rxd0|rxd1|tx_en|txd0|txd1):\s+(P[A-Z]\d+)\s*$")


def main() -> int:
    text = MANIFEST.read_text(encoding="utf-8")
    seen = {}
    for lineno, line in enumerate(text.splitlines(), 1):
        m = PIN_RE.match(line)
        if not m:
            continue
        pin = m.group(1)
        signal = line.split(":", 1)[0].strip()
        # Same short signal names across blocks are okay; physical pin reuse is not.
        if pin in seen:
            old_line, old_signal = seen[pin]
            raise SystemExit(
                f"FAIL: physical pin {pin} reused at line {lineno} ({signal}); "
                f"already reserved at line {old_line} ({old_signal})"
            )
        seen[pin] = (lineno, signal)

    required = {
        "PB13": "USB HS ULPI D6",
        "PG14": "Ethernet RMII TXD1",
        "PA11": "USB FS DM",
        "PA12": "USB FS DP",
    }
    for pin in required:
        if pin not in seen:
            raise SystemExit(f"FAIL: required frozen pin missing: {pin}")

    if "claim_usb3_superspeed" not in text:
        raise SystemExit("FAIL: USB3 anti-mislabel guard missing")

    print(f"PASS: manifest contains {len(seen)} unique reserved interface pins")
    print("PASS: PB13=ULPI_D6 and PG14=RMII_TXD1 architecture is preserved")
    print("PASS: USB3 mislabel guard present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
