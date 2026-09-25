# KiCad V1 Workspace

本目录用于新的 reference-based V1 工程；不从旧 `kicad/stm32h743_core.*` 直接改板。

## Planned files

- `h743_dev_v1.kicad_pro`
- `h743_dev_v1.kicad_sch`
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

## Current gate

在创建实际 schematic 前先完成：

- USB HS PHY exact part review
- Host VBUS power switch selection
- LAN8742A exact package/strap review
- USB-C and USB-A exact connector footprint selection

这些器件未冻结前可以画逻辑网络，但禁止提前把 footprint 当成最终制造输入。
