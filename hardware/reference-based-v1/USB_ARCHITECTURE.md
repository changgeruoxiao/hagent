# USB Architecture — V1

## 1. 端口定义

V1 有两个物理 USB 口，功能明确分工。

### J_USB_FS — USB-C Device/UFP

用途：

- STM32 ROM DFU
- CDC ACM
- HID / 自定义 USB Device
- 调试和固件维护

能力：USB 2.0 Full-Speed，12 Mbit/s。

MCU：PA11/PA12（OTG_FS_DM/DP）。

Type-C 仅按 USB2 UFP 使用：CC1/CC2 配 Rd，不加入 USB-PD。

### J_USB_HS — USB-A Host

用途：

- U 盘
- USB 网卡/串口等外设
- USB2 HS 设备测试

能力：USB 2.0 High-Speed，480 Mbit/s。

路径：

`STM32H743 OTG_HS -> ULPI -> USB3320C/USB3300 class PHY -> D+/D- -> USB-A`

这个端口不是 USB 3.0。即使未来采用带蓝色塑料舌片的 Type-A 连接器，如果没有 SuperSpeed TX/RX 对和 USB3 controller，也仍然只能算 USB2；因此 V1 直接使用规范匹配的 USB2 Host 连接器，避免误导。

## 2. H743 ULPI 固定引脚

| Signal | Pin |
|---|---|
| ULPI_D0 | PA3 |
| ULPI_CK | PA5 |
| ULPI_D1 | PB0 |
| ULPI_D2 | PB1 |
| ULPI_D3 | PB10 |
| ULPI_D4 | PB11 |
| ULPI_D5 | PB12 |
| ULPI_D6 | PB13 |
| ULPI_D7 | PB5 |
| ULPI_STP | PC0 |
| ULPI_DIR | PC2 |
| ULPI_NXT | PC3 |

PC2/PC3 与 `PC2_C/PC3_C` 是不同管脚，原理图 symbol/net 名称必须避免混淆。

## 3. 与 Ethernet 的冲突处理

MB1364 使用 PB13 = RMII_TXD1；ULPI 固定需要 PB13 = D6。

V1：

- PB13 -> ULPI_D6
- PG14 -> RMII_TXD1

PG14 是 STM32H743 datasheet 明确支持的 ETH_MII_TXD1 / ETH_RMII_TXD1 管脚。

## 4. ULPI PHY 选择

首选类别：Microchip USB3320C / USB3300 兼容思路的 Hi-Speed USB 2.0 ULPI PHY。

最终料号冻结前必须确认：

- 2026 可采购性
- QFN 封装与装配能力
- VDDIO=3.3V 兼容
- reference clock 支持
- RBIAS 精度
- internal regulator / external capacitor 要求
- RESETB 时序
- CPEN/VBUS control 行为
- ESD 是否仍需板外补强

不允许凭旧模块原理图猜外围值。

## 5. HS Host VBUS

USB-A Host 的 5V 不能直接硬连系统 5V，必须经过 USB power switch：

- EN：由 GPIO 或 PHY CPEN 控制
- current limit
- short-circuit / thermal protection
- OC/FAULT 回 MCU
- 输出 bulk + local decoupling
- connector VBUS 侧 ESD/TVS 评估

具体 power-switch 型号在 BOM 阶段冻结。

## 6. PCB rules

### USB HS D+/D-

- 目标 90Ω differential
- 同层
- 连续 GND reference
- 少过孔
- 不跨 plane split
- ESD 靠 connector
- PHY 靠 connector
- 禁止 stub

### ULPI

ULPI 是 60MHz 同步并行接口。规则：

- PHY 尽量靠 MCU
- CK 最优先
- DATA[0:7]/DIR/NXT/STP 紧凑
- 不为“漂亮等长”制造蛇形；优先短、直接、连续参考
- 具体 skew/length budget 以 PHY datasheet/ULPI layout guide 为准
- 不允许通用 autorouter 自由处理 ULPI 区域

## 7. 真 USB 3.x 的后续路线

如果后续必须达到 5 Gbit/s SuperSpeed，不改 V1 的 ULPI 方案硬凑。单独评估：

- FT600/FT601 USB3 FIFO bridge
- FPGA + USB3 PHY/controller
- 换带 USB3 controller 的 SoC/MPU

H743 可作为控制 MCU，但不是 USB3 link controller。
