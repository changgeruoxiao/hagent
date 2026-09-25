#!/usr/bin/env python3
"""Fail preflight when frozen interface pins are absent from the selected MCU package."""

from check_pin_reservations import RESERVATIONS

PACKAGE = "STM32H743ZIT6 / LQFP144"
DATASHEET = "DS12110 Rev 11, Figure 7 p.57 and Table 9 p.67"

# In the LQFP144 pin table, digital GPIO PC2 and PC3 are not bonded. Pins 28
# and 29 are PC2_C and PC3_C, analog-only package pins. ULPI DIR/NXT require
# the digital GPIO pins, so they cannot be wired to the _C pins.
UNBONDED_DIGITAL_PINS = {
    "PC2": ("USB_HS_ULPI_DIR", "PC2_C at package pin 28 is analog-only"),
    "PC3": ("USB_HS_ULPI_NXT", "PC3_C at package pin 29 is analog-only"),
}


def main() -> int:
    conflicts = [
        (pin, RESERVATIONS[pin], detail)
        for pin, (signal, detail) in UNBONDED_DIGITAL_PINS.items()
        if RESERVATIONS.get(pin) == signal
    ]
    if conflicts:
        print(f"BLOCKED: {PACKAGE} does not expose the frozen digital ULPI pin map.")
        print(f"Evidence: {DATASHEET}; the PC2/PC3 rows show no LQFP144 pin numbers.")
        for pin, signal, detail in conflicts:
            print(f"  {pin} -> {signal}: {detail}")
        return 1

    print(f"PASS: frozen digital reservations are available on {PACKAGE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
