# H743 精简开发板 V1 — Reference-Based Baseline

> 状态：架构冻结 / 原理图迁移准备阶段  
> 分支：`reference-based-v1`  
> 目标：不再从零自动生成整板，而是以经过实际产品验证的参考设计为黄金基线，裁剪出一块适合日常开发、网口和 USB 可直接使用的 STM32H743ZIT6 开发板。

## 1. V1 目标

首板只解决“拿起来就能开发”的基础能力：

- STM32H743ZIT6，LQFP144
- 4 层 PCB
- 5V 输入、稳定 3.3V 主电源
- HSE + LSE
- NRST / BOOT0
- SWD + SWO
- USB 2.0 Full-Speed Device，USB-C 接口
- 10/100M Ethernet，LAN8742A，RMII，RJ45
- PWR LED + USER LED + USER KEY
- 剩余 GPIO 通过两侧排针引出
- 必要测试点

V1 **不加入**：

- USB HS / ULPI / USB3300
- SDRAM
- QSPI Flash（除非后续软件需求明确需要）
- LCD / 摄像头
- CAN / RS485
- SD 卡
- 板载 ST-LINK
- Arduino / ST Morpho 兼容接口
- Wi-Fi / BLE

目标不是“功能最多”，而是“基础外设不用飞线，首板成功率高，后续可作为长期 H743 实验平台”。

## 2. 黄金参考

### 2.1 ST NUCLEO-H743ZI2 / MB1364 — 一级参考

仓库已经保存：

- `doc/NUCLEO-H743ZI2_MB1364_官方原理图.pdf`
- `doc/AN4938_硬件开发入门.pdf`
- `doc/DS12110_STM32H743xI_数据手册.pdf`
- `doc/ES0392_勘误表.pdf`

MB1364 与本板使用同一 MCU 型号族及 LQFP144 封装，其 MCU 电源、VCAP、VDD33_USB、复位、BOOT、SWD、USB FS 和 Ethernet 连接方式作为 V1 的首要交叉核验依据。

**规则：Ethernet 和 USB 子系统禁止由 Agent 自由发明拓扑。**

### 2.2 WeAct STM32H7 核心板 — 二级参考

仓库已经保存：

- `doc/WeAct_STM32H7xx_核心板_原理图_V12.pdf`

用于交叉核对：

- 独立 HSE 晶振
- USB-C Device / DFU
- 小型核心板的电源与启动策略

WeAct 与本板型号/封装不完全一致，不能机械复制。

### 2.3 当前自动 EDA 板 — 三级参考 / 实验成果

当前 `main` 上的 `kicad/stm32h743_core.*` 和自动生成脚本继续保留，用于：

- MCU 最小系统连接交叉核对
- DRC/网表自动检查能力复用
- BOM/制造文件流水线复用

但不再把“自动生成出来且 DRC=0”视为可投板的充分条件。

## 3. 固定引脚资源

### 3.1 Ethernet / LAN8742A / RMII

V1 固定采用与 STM32H743 Nucleo 方案一致的 RMII 引脚组合：

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
| TXD1 | PB13 |

这些引脚在 V1 中标记为 **ETH 专用**，不能再被排针定义为默认自由 GPIO。

PHY 侧的时钟、strap、RBIAS、复位、模拟电源去耦、磁性器件及 RJ45 连接方式必须逐项对照 MB1364/LAN8742A 数据手册审核。

### 3.2 USB FS

| USB 信号 | STM32H743 |
|---|---|
| USB_FS_DM | PA11 |
| USB_FS_DP | PA12 |
| USB_FS_VBUS | PA9（按最终 VBUS-sense 策略决定是否接入） |

USB-C 仅实现 USB 2.0 FS Device/UFP：

- CC1/CC2 各自 Rd
- D+/D- ESD
- 不加入 USB-PD
- 不加入 ULPI
- 不加入 USB3300
- 不把 Type-C 连接器当成 USB Host 电源输出口

### 3.3 调试 / 时钟

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
- LAN8742A 必须靠近 RJ45，PHY 到磁性器件的 MDI 差分线短、对称、少过孔。
- RMII 50MHz 时钟路径优先人工布局和人工/约束布线。
- USB D+/D- 同层、连续参考平面、避免 stub。
- MCU 每组去耦必须就近，不允许为了自动布线把去耦“搬远”。
- VCAP 电容必须就近。
- HSE/LSE 下方不穿越普通高速/开关信号。
- 开关电源热回路不得由通用自动布线器决定。
- Ethernet、USB、晶振、电源四个区域完成后先人工审核，再开放普通 GPIO 自动布线。

## 5. Agent 可做 / 不可做

### Agent 可直接执行

- 从参考设计提取网络表和器件连接关系
- 建立 KiCad 原理图
- 建立封装/BOM 清单
- 检查 MCU 引脚冲突
- ERC / DRC
- 自动检查 VCAP/VDD/VDDA/VREF/VDD33_USB
- BOM 替代料筛选
- 普通 GPIO 布线
- Gerber/BOM/CPL 生成
- 生成 bring-up 测试程序与验收表

### 必须经过人工或第二代理独立复核

- 电源芯片外围补偿和功率回路
- Ethernet PHY strap / clock / RBIAS
- PHY 到 RJ45 MDI 差分
- USB 差分布线
- 晶振网络
- 叠层和阻抗
- 首次投板 Gerber

### 禁止

- 只因为 ERC/DRC 为 0 就宣称“可投板”
- 为了解决布线拥堵修改已冻结的 Ethernet/USB 引脚
- 自动把内层 GND 改为普通信号层
- 未查 datasheet 就修改 strap、补偿、电源值
- 为了减少器件数量删除 ESD/去耦/VCAP/关键偏置器件

## 6. 首板成功定义

首板至少完成：

1. 3.3V 上电正常，无异常发热
2. NRST / BOOT0 正常
3. SWD 能稳定识别、下载、单步
4. HSE 可运行目标时钟
5. LSE 可正常起振（若装）
6. USB DFU/CDC 至少一种方式稳定枚举
7. Ethernet PHY ID 可读
8. RJ45 link 可稳定建立
9. DHCP 或静态 IP 可 ping
10. 连续网络收发测试无明显丢包/复位
11. 所有保留 GPIO 无硬件短路/占用冲突

达到以上条件后，才给该 PCB 打 `hardware-verified-v1` 标签。