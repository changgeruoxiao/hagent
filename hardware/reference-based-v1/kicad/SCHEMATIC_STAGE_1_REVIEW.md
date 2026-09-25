# Schematic Stage 1 Review

Date: 2026-09-25

Status: reviewable draft; not a fabrication release

## Scope

`h743_dev_v1.kicad_sch` contains the STM32H743ZIT6 MCU core, 5 V to 3.3 V
conversion, MCU supply and reference connections, HSE/LSE, NRST, BOOT0, SWD,
SWO, and test points. USB FS, USB HS PHY, Ethernet PHY, board connectors, GPIO
headers, and the PCB are not implemented in this stage.

Project-local symbols and the KiCad project are in this directory. The BOM and
ERC report are generated from the current schematic.

## Implementation notes

- All 11 MCU VDD pins and VDD33_USB are tied to +3V3. The 11 VDD pins each
  have a 100 nF bypass capacitor; bulk bypass and additional 1 uF / 100 nF
  capacitors are included on the rail. Physical capacitor placement remains a
  PCB task.
- VCAP1 and VCAP2 share the VCAP net and each have a 2.2 uF capacitor to GND.
- VDDA is fed through a ferrite bead; VREF+ is linked through 0R and has local
  capacitors. VBAT is tied to +3V3 through 0R and locally bypassed. PDR_ON has a
  10 kOhm pull-up.
- The TPS54331DDAR 3.3 V buck stage follows the TI TPS54331 3.3 V application
  example. The input connector, output load, thermal margin, inductor, diode,
  output capacitors, and compensation values still need power-budget and
  layout review. These values are provisional, not frozen purchasing choices.
- HSE is shown as 25 MHz / CL=10 pF with preliminary 15 pF load capacitors;
  LSE is 32.768 kHz / CL=7 pF with preliminary 10 pF load capacitors. Select
  exact crystals and recalculate for their CL, MCU pin capacitance, and board
  parasitics before layout.
- NRST has a 10 kOhm pull-up, 100 nF capacitor, reset switch, and test point.
  BOOT0 has a 10 kOhm pull-down and a 3-pin selection header. The 6-pin debug
  header exposes 3V3, SWDIO, SWCLK, SWO, NRST, and GND.
- J1 is a logical 5 V input and intentionally has no footprint. External
  connector, switch, and crystal footprints must be checked against selected
  orderable parts before PCB use.

## Checks performed

- `check_pin_reservations.py`: pass, 31 reserved pins with PG14=ETH_TXD1 and
  PB13=ULPI_D6 preserved.
- `validate_manifest.py`: pass, 24 unique interface pins and the USB2
  High-Speed labeling guard are present.
- Exported-netlist spot check: pass for the 11 VDD pins plus VDD33_USB, shared
  VCAP capacitors, HSE/LSE, SWD/SWO, PG14=ETH_TXD1, and PB13=ULPI_D6.
- KiCad 10.0.4 ERC: 0 errors, 22 warnings. All 22 are `isolated_pin_label`
  warnings for intentionally reserved but not-yet-implemented USB/Ethernet
  nets: 9 RMII, 3 USB FS, and 10 bonded ULPI signals.
- Local preflight is intentionally incomplete: `check_package_pin_support.py`
  reports OI-001. See `../OPEN_ISSUES.md`; the checker must remain blocking.

Reference cross-checks: ST DS12110 Rev 11, AN4938, NUCLEO-H743ZI2 MB1364
sheet 4, and the TI TPS54331 data sheet/application example. Crystal load
values are explicitly provisional and remain subject to exact-part review.

## Blocking item

The frozen USB HS map assigns ULPI_DIR and ULPI_NXT to digital PC2 and PC3.
On STM32H743ZIT6 LQFP144, those digital GPIOs are not bonded; package pins 28
and 29 are analog-only PC2_C and PC3_C. The schematic leaves both package pins
no-connect. Do not route ULPI or begin PCB floorplanning until the MCU/package
or USB HS requirement is revised through the project architecture documents.

## Generated files

- `h743_dev_v1.kicad_sch` — editable schematic source
- `h743_dev_v1.kicad_pro` — KiCad project
- `hagent.kicad_sym`, `sym-lib-table` — project-local symbol definitions
- `h743_dev_v1-bom.csv` — current provisional BOM
- `h743_dev_v1-erc.rpt` — KiCad ERC output
- `h743_dev_v1.pdf` — visual schematic export
