# KiCad V1 Workspace

本目录用于新的 reference-based V1 工程；不从旧 `kicad/stm32h743_core.*` 直接改板。

## Current status

The first schematic stage is implemented in `h743_dev_v1.kicad_sch`: MCU core,
5 V to 3.3 V power, decoupling, clocks, reset, BOOT0 selection, SWD/SWO, and
test points. `h743_dev_v1.kicad_pro`, the project-local `hagent.kicad_sym`, and
`sym-lib-table` make this a standalone KiCad project.

See [`SCHEMATIC_STAGE_1_REVIEW.md`](SCHEMATIC_STAGE_1_REVIEW.md) for the scope,
provisional component choices, netlist spot checks, ERC report, and open
package blocker. The exported BOM, ERC report, and schematic PDF are alongside
the KiCad project.

This is not a complete board design. ERC currently has zero errors and 22
intentional isolated-label warnings for the not-yet-built Ethernet and USB
subsystems. `../OPEN_ISSUES.md` records a package conflict that blocks the
frozen ULPI DIR/NXT map: the selected LQFP144 part does not bond digital PC2 or
PC3. Do not route USB HS until that issue is resolved.

## Planned files

- `h743_dev_v1.kicad_pro`
- `h743_dev_v1.kicad_sch`
- `hagent.kicad_sym` (project-local MCU/ERC-safe VCAP and TPS54331 symbols)
- `sym-lib-table`
- `h743_dev_v1.kicad_pcb`

## Source of truth

生成/绘制前必须读取：

1. `../DESIGN_MANIFEST.yaml`
2. `../PINMAP.md`
3. `../USB_ARCHITECTURE.md`
4. `../REFERENCE_MATRIX.md`

## Sheet split

- MCU_CORE
- POWER
- CLOCK_RESET_DEBUG
- USB_FS
- USB_HS_ULPI
- ETHERNET
- IO_HEADERS

## Remaining gates before external-interface and PCB work

Before adding external interfaces or treating any footprint as a manufacturing
input, complete:

- USB HS PHY exact part review
- Host VBUS power switch selection
- LAN8742A exact package/strap review
- USB-C and USB-A exact connector footprint selection
- Resolution of `OI-001` in `../OPEN_ISSUES.md`

这些器件未冻结前可以画逻辑网络，但禁止提前把 footprint 当成最终制造输入。
