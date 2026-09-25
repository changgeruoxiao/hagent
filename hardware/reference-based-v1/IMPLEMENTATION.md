# Reference-Based V1 实施清单

任何 Agent 接手时先阅读 `BASELINE.md`、`PINMAP.md`、`USB_ARCHITECTURE.md`。

## Phase 0 — 冻结需求

- [x] MCU 固定 STM32H743ZIT6 / LQFP144
- [x] USB FS：USB-C Device/UFP，12 Mbit/s
- [x] USB HS：外置 ULPI PHY，USB2 High-Speed 480 Mbit/s
- [x] USB HS 默认物理口：USB-A Host
- [x] 明确不宣称 USB3 SuperSpeed
- [x] Ethernet 固定 LAN8742A / RMII / 10-100M
- [x] RMII_TXD1 改 PG14，释放 PB13 给 ULPI_D6
- [x] 不做板载 ST-LINK
- [x] 4 层板
- [x] 保留 GPIO 排针
- [ ] 确认最终板框尺寸
- [ ] 确认 RJ45、USB-A HS、USB-C FS 三个接口相对位置
- [ ] 确认 5V 输入是否只保留 USB-C + 5V 排针
- [ ] USB HS PHY 最终料号采购性冻结（USB3320C / USB3300 同类）

## Phase 1 — 参考设计拆解

### MCU / power
- [ ] MCU power / VCAP / VDDA / VREF / VDD33_USB
- [ ] NRST / BOOT0 / PDR_ON / VBAT
- [ ] SWD / SWO

### Ethernet
- [ ] LAN8742A
- [x] RMII pin map
- [ ] PHY clock
- [ ] PHY strap
- [ ] PHY reset
- [ ] PHY power / decoupling / RBIAS
- [ ] RJ45 / magnetics / LED

### USB FS
- [ ] USB FS Device circuit
- [ ] USB-C CC1/CC2 Rd
- [ ] ESD
- [ ] VBUS detect

### USB HS / ULPI
- [x] ULPI MCU pin map
- [ ] USB3320C/USB3300 PHY power tree
- [ ] PHY reference clock / REFSEL
- [ ] PHY RBIAS
- [ ] PHY RESETB
- [ ] ULPI bus electrical review
- [ ] USB-A Host VBUS high-side current-limit switch
- [ ] over-current feedback
- [ ] HS D+/D- ESD strategy
- [ ] connector shield / chassis-ground strategy

输出：`REFERENCE_MATRIX.md` 与 `USB_ARCHITECTURE.md`

## Phase 2 — V1 原理图

建立新的 KiCad 工程，不直接修改旧自动生成板：

```
hardware/reference-based-v1/kicad/
  h743_dev_v1.kicad_pro
  h743_dev_v1.kicad_sch
  h743_dev_v1.kicad_pcb
```

原理图建议分层：

1. MCU_CORE
2. POWER
3. CLOCK_RESET_DEBUG
4. USB_FS
5. USB_HS_ULPI
6. ETHERNET
7. IO_HEADERS

门禁：

- [ ] ERC 通过
- [ ] 与 STM32H743ZIT6 datasheet 引脚表交叉核对
- [ ] 运行 `check_pin_reservations.py`
- [ ] 与参考设计对应网络逐项 parity check
- [ ] Ethernet 与 USB HS 无 pin mux 冲突
- [ ] 两路 USB VBUS 角色无反向供电风险

## Phase 3 — PCB Floorplan

先布局，不布普通 GPIO：

- [ ] MCU 中央
- [ ] USB-C FS 靠板边
- [ ] USB-A HS 靠板边
- [ ] ULPI PHY 紧邻 MCU 与 HS connector
- [ ] RJ45 靠板边
- [ ] LAN8742A 靠 RJ45
- [ ] PHY 25MHz / RMII REF_CLK 区域固定
- [ ] ULPI 60MHz 时钟与 DATA[0:7] 区域固定
- [ ] HSE/LSE 靠 MCU
- [ ] 去耦与 VCAP 完成
- [ ] 电源热回路完成
- [ ] SWD 靠板边
- [ ] GPIO 排针定位
- [ ] 安装孔定位

输出 floorplan 截图进行人工审查。

## Phase 4 — 关键网络先布

顺序固定：

1. 电源热回路
2. MCU 去耦 / VCAP
3. HSE/LSE
4. USB HS PHY 本地电源/时钟/RBIAS
5. ULPI CK + control + DATA bus
6. USB HS D+/D-
7. Ethernet MDI
8. Ethernet RMII/REF_CLK
9. USB FS D+/D-
10. SWD
11. 其余 GPIO

关键网络结束后第二次审查。

## Phase 5 — 普通信号与自动化

允许 Agent/自动布线器参与：

- GPIO 排针
- LED / KEY
- 低速控制信号

不能自动自由处理：

- USB HS ULPI
- USB HS/FS 差分对
- Ethernet RMII/MDI
- 晶振
- 电源热回路

## Phase 6 — 投板门禁

- [ ] ERC 0 error
- [ ] DRC 0 error
- [ ] 0 unconnected
- [ ] pin-reservation checker 通过
- [ ] BOM 完整
- [ ] footprint 与实物料号一一核验
- [ ] RJ45 footprint 核验
- [ ] USB-A / USB-C footprint 核验
- [ ] ULPI PHY footprint/pin1 核验
- [ ] LAN8742A footprint/pin1 核验
- [ ] MCU footprint/pin1 核验
- [ ] USB HS 90Ω 差分约束核验
- [ ] USB FS 90Ω 差分约束核验
- [ ] ULPI 60MHz 关键走线人工审查
- [ ] Gerber / Drill / Board outline 人工查看
- [ ] 铜到板边、丝印极性/Pin1 检查
- [ ] 第二人/第二 Agent 独立 schematic audit

## Phase 7 — Bring-up

1. 空板短路检查
2. 电源
3. MCU + SWD
4. HSE/LSE
5. USB FS
6. ULPI PHY
7. USB HS Host + HS device enumeration
8. LAN8742A
9. RJ45
10. Ethernet + USB HS 并发
11. GPIO

测试结果记录到 `BRINGUP.md`。
