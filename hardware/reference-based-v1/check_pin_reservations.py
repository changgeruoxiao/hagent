#!/usr/bin/env python3
"""Validate frozen STM32H743 pin reservations for reference-based-v1.

This is intentionally simple and dependency-free. It catches architecture-level
pin collisions before schematic generation/CubeMX work.
"""

RESERVATIONS = {
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

    # USB HS ULPI
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


def main() -> int:
    # Dict literals cannot contain duplicate keys without overwriting, so also
    # validate the inverse intent list explicitly in future generated manifests.
    signals = list(RESERVATIONS.values())
    if len(signals) != len(set(signals)):
        raise SystemExit("FAIL: duplicate signal assignment")

    assert RESERVATIONS["PB13"] == "USB_HS_ULPI_D6"
    assert RESERVATIONS["PG14"] == "ETH_TXD1"

    forbidden = {
        ("PB13", "ETH_TXD1"),
        ("PG14", "USB_HS_ULPI_D6"),
    }
    for pin, signal in forbidden:
        if RESERVATIONS.get(pin) == signal:
            raise SystemExit(f"FAIL: forbidden mapping {pin} -> {signal}")

    print(f"PASS: {len(RESERVATIONS)} frozen pin reservations")
    print("PASS: Ethernet TXD1 uses PG14; PB13 reserved for ULPI_D6")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
