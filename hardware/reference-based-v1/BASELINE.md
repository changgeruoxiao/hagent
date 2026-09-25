# H743 精简开发板 V1 — Reference-Based Baseline

> 状态：架构冻结 / 原理图迁移准备阶段  
> 分支：`reference-based-v1`  
> 目标：以成熟参考设计为基线，裁剪出一块适合日常开发、Ethernet 与两路 USB 可直接使用的 STM32H743ZIT6 开发板。

## 1. V1 目标

首板解决“拿起来就能开发”的基础能力：

- STM32H743ZIT6，LQFP144
- 4 层 PCB
- 5V 输入、稳定 3.3V 主电源
- HSE + LSE
- NRST / BOOT0
- SWD + SWO
- **USB-A：USB 2.0 High-Speed Host，480 Mbit/s，外置 ULPI PHY**
- **USB-C：USB 2.0 Full-Speed Device/UFP，12 Mbit/s，DFU/CDC 调试优先**
- 10/100M Ethernet，LAN8742A，RMII，RJ45
- PWR LED + USER LED + USER KEY
- 剩余 GPIO 通过两侧排针引出
- 必要测试点

### 关于“USB 3.0”

STM32H743 原生只有 1×USB OTG FS 和 1×USB OTG HS/FS；其 HS 模式通过 ULPI 外置 PHY 工作于 **USB 2.0 High-Speed 480 Mbit/s**。它没有 USB 3.x SuperSpeed PHY/控制器，因此 V1 不把任何端口标成“USB 3.0 / 5 Gbit/s”。

若以后确实需要 USB 3.x，另开 V2 子项目评估 FT600/FT601 一类 SuperSpeed FIFO Bridge、FPGA 或更高阶 SoC；不得通过换一个蓝色 USB-A 插座来宣称 USB 3.0。

V1 **暂不加入**：

- 真正 USB 3.x SuperSpeed
- SDRAM
- QSPI Flash（除非后续软件需求明确需要）
- LCD / 摄像头
- CAN / RS485
- SD 卡
- 板载 ST-LINK
- Arduino / ST Morpho 兼容接口
- Wi-Fi / BLE

## 2. 黄金参考

### 2.1 ST NUCLEO-H743ZI2 / MB1364 — MCU / Ethernet / USB FS 一级参考

仓库已有：

- `doc/NUCLEO-H743ZI2_MB1364_官方原理图.pdf`
- `doc/AN4938_硬件开发入门.pdf`
- `doc/DS12110_STM32H743xI_数据手册.pdf`
- `doc/ES0392_勘误表.pdf`

MB1364 用于 MCU 电源、VCAP、VDD33_USB、复位、BOOT、SWD、USB FS 和 Ethernet 的交叉核验。

**Ethernet 和 USB 子系统禁止由 Agent 自由发明拓扑。**

### 2.2 ST 的 H7 + ULPI PHY 参考设计 / Microchip ULPI 资料 — USB HS 一级参考

USB HS 不从 MB1364 推导。优先参考：

- STM32H743 datasheet / RM0433 的 OTG_HS + ULPI 规定
- ST 采用 USB3320C 类 ULPI PHY 的官方 H7 参考设计
- Microchip USB3300 / USB3320 datasheet
- Microchip AN1917 ULPI Design Guide
- Microchip AN1310 USB3300 PHY Layout Guidelines

V1 暂定采用 **USB3320C / USB3300 同类 32-QFN ULPI PHY**；最终具体料号在 BOM 可采购性审核后冻结。

### 2.3 WeAct STM32H7 核心板 — 二级参考

用于交叉核对独立 HSE、USB-C Device/DFU、小型核心板启动策略，不机械复制。

### 2.4 当前自动 EDA 板 — 三级参考 / 实验成果

旧 `kicad/stm32h743_core.*` 与脚本保留，用于最小系统交叉核验、ERC/DRC/BOM/制造流水线复用；不再把 DRC=0 视为可投板充分条件。

## 3. 固定引脚资源

### 3.1 Ethernet / LAN8742A / RMII

| RMII 信号 | STM32H743 |
|---|---|
| REF_CLK | PA1 |
| MDIO | PA2 |
| MDC | PC1 |
| CRS_DV | PA7 |
| RXD0 | PC4 |
| RXD1 | PC5 |
| TX_EN | PG11 |
| TXD0 | PG13 |
| TXD1 | **PG14** |

注意：MB1364 使用 PB13 作为 RMII_TXD1，但 V1 需要 PB13 给 ULPI_D6。STM32H743 datasheet 明确 PG14 也支持 ETH_RMII_TXD1，因此 V1 有意切换到 PG14。此项为冻结的、可追溯的参考设计偏离。

### 3.2 USB FS — 普通/维护口

| USB 信号 | STM32H743 |
|---|---|
| USB_FS_DM | PA11 |
| USB_FS_DP | PA12 |
| USB_FS_VBUS | PA9（最终 VBUS-sense 策略确认后接入） |

默认接口：USB-C Device/UFP。

- CC1/CC2 各自 Rd
- D+/D- ESD
- 不做 USB-PD
- 用于 DFU / CDC / HID / 普通设备模式
- 不承担 Host 5V 输出

### 3.3 USB HS — 高速口

USB HS 通过外置 ULPI PHY 实现，目标 480 Mbit/s。

| ULPI 信号 | STM32H743 |
|---|---|
| D0 | PA3 |
| CK | PA5 |
| D1 | PB0 |
| D2 | PB1 |
| D3 | PB10 |
| D4 | PB11 |
| D5 | PB12 |
| D6 | PB13 |
| D7 | PB5 |
| STP | PC0 |
| DIR | PC2 |
| NXT | PC3 |

默认接口角色：**USB-A Host**。

- PHY → USB-A 只使用 USB2 D+/D-/VBUS/GND 触点
- 5V VBUS 必须通过限流高边开关/电源开关，不允许 MCU 直接供电
- 需要过流检测
- D+/D- 走线按 USB2 HS 90Ω 差分设计
- ULPI 60MHz 总线为关键数字网络，必须短、连续参考平面、避免无控制自动布线
- 不使用 USB 3.0 SuperSpeed TX/RX 差分对

若以后需要把 HS 口改为 Device/OTG，优先在原理图阶段改接口与 VBUS/ID/CC 策略，不改变 ULPI 总线本身。

### 3.4 调试 / 时钟

- SWDIO: PA13
- SWCLK: PA14
- SWO: PB3
- HSE: PH0 / PH1
- LSE: PC14 / PC15
- NRST 单独引出
- BOOT0 提供明确跳线/按键策略

## 4. PCB 约束

V1 固定 4 层：

1. L1：器件 + 关键信号
2. L2：完整 GND
3. L3：电源为主
4. L4：普通信号 + GND

硬约束：

- L2 不允许被普通信号切割。
- LAN8742A 靠近 RJ45；PHY 到磁性器件 MDI 差分短、对称、少过孔。
- RMII 50MHz REF_CLK 与 ULPI 60MHz 时钟优先人工布局和约束布线。
- USB FS 与 USB HS 的 D+/D- 分别独立成对，不交叉绕行。
- ULPI PHY 靠近 MCU 与 HS USB 连接器形成紧凑三角区域。
- ULPI DATA[0:7]/CK/DIR/NXT/STP 不允许交给无约束全板自动布线。
- MCU 每组去耦、VCAP 必须就近。
- HSE/LSE 下方不穿越普通高速/开关信号。
- 开关电源热回路不得由通用自动布线器决定。
- Ethernet、USB FS、USB HS、晶振、电源五个区域完成后先人工审核，再开放普通 GPIO 自动布线。

## 5. Agent 可做 / 不可做

### Agent 可直接执行

- 从参考设计提取网络和器件连接关系
- 建立 KiCad 原理图
- 建立封装/BOM 清单
- 检查 MCU 引脚冲突
- ERC / DRC
- 自动检查 VCAP/VDD/VDDA/VREF/VDD33_USB
- 自动检查冻结引脚表唯一性
- BOM 替代料筛选
- 普通 GPIO 布线
- Gerber/BOM/CPL 生成
- bring-up 测试程序与验收表

### 必须经过人工或第二代理独立复核

- 电源外围与功率回路
- Ethernet PHY strap / clock / RBIAS
- PHY 到 RJ45 MDI
- USB FS 差分
- USB HS PHY 时钟、RBIAS、VBUS 与 ULPI
- USB HS D+/D-
- ULPI 60MHz 总线
- 晶振网络
- 叠层和阻抗
- 首次投板 Gerber

### 禁止

- 只因为 ERC/DRC 为 0 就宣称“可投板”
- 为解决拥堵修改已冻结的 Ethernet/USB 引脚
- 把 USB2 HS 480M 写成 USB3 5G
- 用 USB3 蓝色插座的外观代替 SuperSpeed 电气实现
- 自动把内层 GND 改为普通信号层
- 未查 datasheet 就修改 strap、RBIAS、补偿、电源值
- 为减少器件删除 ESD/去耦/VCAP/关键偏置

## 6. 首板成功定义

首板至少完成：

1. 3.3V 上电正常，无异常发热
2. NRST / BOOT0 正常
3. SWD 稳定识别、下载、单步
4. HSE / LSE 按设计运行
5. USB FS DFU/CDC 至少一种稳定枚举
6. USB HS PHY 可通过 ULPI 初始化
7. USB HS Host 能枚举至少一个 USB2 HS U 盘/设备，并确认以 High-Speed 连接
8. Ethernet PHY ID 可读
9. RJ45 link 稳定建立
10. DHCP 或静态 IP 可 ping
11. Ethernet 与 USB HS 同时工作时无引脚冲突/异常复位
12. 所有保留 GPIO 无硬件短路/占用冲突

达到以上条件后，才给该 PCB 打 `hardware-verified-v1` 标签。
