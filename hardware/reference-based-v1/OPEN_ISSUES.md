# Open Issues — Reference-Based V1

## OI-001 — Frozen ULPI DIR/NXT pins are not bonded on STM32H743ZIT6 LQFP144

**Status:** Blocking for USB HS / ULPI implementation and PCB floorplanning.

### Frozen assignment

`PINMAP.md`, `DESIGN_MANIFEST.yaml`, and `USB_ARCHITECTURE.md` assign:

- `USB_HS_ULPI_DIR` → digital GPIO `PC2`
- `USB_HS_ULPI_NXT` → digital GPIO `PC3`

The current MCU choice is `STM32H743ZIT6`, LQFP144.

### Evidence

In ST datasheet `DS12110 Rev 11`:

- Figure 7, page 57, labels LQFP144 package pins 28 and 29 as `PC2_C` and `PC3_C`.
- Table 9, page 67, lists the digital `PC2` and `PC3` rows with no LQFP144 pin number. Those rows carry the `OTG_HS_ULPI_DIR` and `OTG_HS_ULPI_NXT` alternate functions.
- Table 9 identifies `PC2_C` and `PC3_C` as analog-only pins. They are not substitutes for the digital GPIOs.

The generated V1 schematic therefore leaves the physical `PC2_C` and `PC3_C` pins explicitly no-connect and does not assign ULPI DIR/NXT to them. The reserved net names are not present on U1 in this package.

### Impact

The frozen ULPI interface is incomplete with the selected MCU/package. USB HS PHY initialization and USB-A Host operation cannot work with this mapping. Do not start ULPI routing or represent this schematic stage as having a complete USB HS interface.

### Candidate paths

1. Evaluate an STM32H743 package/device variant that bonds digital PC2 and PC3 (the same datasheet lists larger packages with those GPIOs), then recheck every reserved pin, orderable code, footprint, board outline, and GPIO header map.
2. Select another MCU/package that supports the frozen Ethernet and ULPI requirements, then update the baseline and all pin-source documents together.
3. Remove USB HS/ULPI from V1 and revise the product requirements to USB FS only. This changes the frozen V1 capability.

**Recommendation:** evaluate the larger H743 package first to preserve the intended USB2 High-Speed Host feature. No architecture choice has been applied in this branch.
