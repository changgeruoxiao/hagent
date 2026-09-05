# STM32H743ZIT6 最小系统核心板 · 设计规格书

| 项目 | 内容 |
|---|---|
| 文档版本 | v1.1（2026-09-05） |
| 产品定位 | 最小系统核心板（供电 + 时钟 + 复位/启动 + 调试 + USB + 全 IO 引出） |
| 主控 | STM32H743ZIT6（LQFP144，20×20mm，0.5mm pitch，Cortex-M7 @ 480MHz，2MB Flash / 1MB SRAM） |
| 叠层 | 4 层（信号 / GND / 电源 / 信号），板厚 1.6mm |
| 板尺寸 | 85 × 65mm，四角 M3 安装孔 |
| 实施方式 | KiCad 全脚本自动生成（本文档即自动化实施的"契约"，每条规则将写入生成脚本与 DRC 约束） |

---

## 1. 系统框图

```
                 ┌────────────────────────────────────────────┐
  USB-C 5V ──保险丝──┬──► SS34 合路 ──► TPS54331 DCDC ──► 3.3V 轨 ──┬──► STM32H743ZIT6 (LQFP144)
  5VIN 排针 ─────────┘        (5V→3.3V/2A)      │ 0Ω测流          │    ├─ VDD×N 每脚100nF + 2×4.7µF
                                                  └─ PWR LED        ├─ VDDA/VREF 磁珠+滤波
                                                                    ├─ VCAP ×2 各2.2µF
                                                                    ├─ PDR_ON 10k上拉
                 8MHz HSE ──► OSC_IN/OUT (PH0/PH1)                ┤
                 32.768kHz LSE ──► OSC32_IN/OUT (PC14/PC15)       ├─► 全部剩余IO ──► 两侧 2×26 双排针
                 NRST: 按键+100nF ──► NRST                         │
                 BOOT0: 3P跳线+100k下拉 ──► BOOT0                  ├─ PB0 ── USER LED
                 SWD 排针 ──► PA13(SWDIO)/PA14(SWCLK)/PB3(SWO)     └─ PC13 ── USER KEY
                 USB D+/D- ──USBLC6──► PA11/PA12 (USB FS, DFU可用)
```

**默认供电路径**：USB-C（5V），或排针 5VIN，两路经各自肖特基合路防倒灌。

---

## 2. 电源子系统

### 2.1 输入与 5V→3.3V DCDC

| 项 | 规格与取值 |
|---|---|
| 输入电压 | 5V ±5%（USB-C VBUS 或 5VIN 排针，SS34 肖特基二路合流） |
| 输入保护 | 自恢复保险丝 0.5A（USB 路串联） |
| DCDC | TPS54331DDAR（SOIC-8 带散热盘，3.5–28V 输入，3A，570kHz 固定频率，**外置 II 型补偿**——实施时据数据手册 Table 5-1 更正：COMP 为独立引脚，非内部补偿） |
| 功率预算 | 3.3V 输出按 1A 设计（H743 满频典型 ~300mA，留 3 倍裕量） |
| 电感 | 6.8µH / ≥3.5A 屏蔽功率电感，7.3×6.6mm（数据手册 §8.2.2.5：6.8µH–47µH 区间，例程 6.8µH/3.6A） |
| 续流二极管 | SS34（SMA），数据手册例程为 B340A，同类 |
| 反馈分压 | Vref=0.8V：Rtop=10.2kΩ，Rbottom=3.24kΩ（均 1%，数据手册 §8.2.2.4 例程值）→ Vout=3.31V |
| 补偿网络 | II 型：RZ=29.4kΩ（COMP 串联）、CZ=1000pF（RZ 下端对地）、CP=47pF（COMP 对地）——数据手册 §8.2.2.7 例程值 |
| EN / SS | 悬空（EN 内部上拉使能；SS 用内部默认斜率） |
| BOOT 电容 | 100nF（BOOT—PH 引脚间，必装） |
| 输出电容 | 2×47µF X5R 1206（数据手册例程值，稳定性优先） |
| 输入电容 | 2×10µF 25V X7R 0805 + 100nF |
| 测流设计 | 3.3V 主轨串 0Ω 电阻 R_SEL，首板调试时可换电流表串联 |

> 备选：若对效率不敏感可换 AMS1117-3.3，但 (5−3.3)V×0.3A≈0.5W 发热明显，不推荐。

### 2.2 MCU 电源细节（依据 AN4938）

| 引脚/网络 | 处理规则 |
|---|---|
| VDD/VSS 每对 | 各 1×100nF（X7R，0402），**放置距离对应引脚 ≤3mm**，电容地端独立双过孔下到 L2 |
| 整体储能 | 靠近 MCU 2×4.7µF |
| VDDA | VDD 经磁珠（600Ω@100MHz）→ VDDA，1µF + 10nF 到 VSSA |
| VREF+ / VREF− | VREF+ 接 1µF + 100nF；VREF− 接 VSSA；预留 3P 跳线可选外部基准（默认接 3.3V） |
| VCAP（内部 1.2V 核 LDO） | **每个 VCAP 引脚 1×2.2µF 低 ESR 陶瓷电容**（LQFP144 上共 2 个 VCAP，全部就近单独接地，不允许共用远端电容） |
| VDD33_USB（USB 域电源，pin 95） | 接 3.3V 主轨，**就近 1µF + 100nF** 去耦（DS12110 修订版电源方案明确新增该 1µF 要求）；此脚不供电则 USB 外设无法工作。VDD50USB 在 LQFP144 上未引出（内部连接），无需处理。**四方证据已核验**：DS12110 引脚表（LQFP144=95，注意 pypdf 提取时该名被截断为 VDD33US）/ Figure 7 引脚图 / 官方 NUCLEO-H743ZI2 原理图（网络 VDD33_USB 接 3.3V 域）/ KiCad 符号（对照详情见附录 B） |
| PDR_ON | 10kΩ 上拉到 VDD，并引测试点（上拉 = 使能上电复位/PDR；需排查时可强制拉低） |
| VBAT | 0Ω 直连 3.3V（核心板不装纽扣电池；留焊盘可改） |
| BOOT0 | 100kΩ 下拉到 GND（常驻）+ 3P 跳线（3V3 / 悬空 / GND），默认插 GND 位 |

> 实施注意：VDD/VSS/VCAP 在 LQFP144 上的**具体引脚号已与 DS12110 交叉核验（见附录 A）**，生成脚本仍从 KiCad 符号 `MCU_ST_STM32H7:STM32H743ZITx` 自动提取，不手工抄写，避免抄错。

### 2.3 上电时序与监控

- H743 无外部 POR 监控需求（内部 PDR + BOR 完备），NRST 由片内上拉保持，见 §4。
- DCDC SS 引脚悬空（内部软启动），上电斜率满足 MCU 要求。

---

## 3. 时钟子系统

| 时钟源 | 器件 | 关键参数 | 负载电容 |
|---|---|---|---|
| HSE 8MHz | 3215 贴片晶振（2 脚；原定 3225 四脚，因 KiCad 官方库无 2 脚 3225 封装改为 3215，8MHz 3215 同样量大价廉） | ±10ppm，CL=12pF | 2×18pF（C1=C2≈2×(CL−Cstray)，Cstray 按 3pF 估） |
| LSE 32.768kHz | 3215 贴片晶振 | ±20ppm，CL=12.5pF | 2×18pF（投产前按所购晶振规格书复算） |

布局规则：
- 两颗晶振紧邻各自 OSC 引脚（≤5mm 走线），下方 L2 保持完整 GND。
- 晶振区域外围包地（guard ring + 缝合过孔），区域内部**禁止任何其它信号穿越**（含 L3/L4）。
- 8MHz → PLL1（÷1 ×120 ÷2）= 480MHz CPU；USB FS 时钟用**片内 HSI48 + CRS（SOF 同步）**，不依赖 HSE 频率搭配。
- ⚠ H743 早期步进存在 LSE 启动相关勘误（见 doc/ES0392_勘误表.pdf），**采购时要求最新步进**，LSE 不起振时优先查勘误条目而非硬件。

---

## 4. 复位与启动

| 信号 | 电路 |
|---|---|
| NRST | 片内已有上拉；外部 1×100nF 到 GND + 轻触按键（并联 100nF）+ 测试点 |
| BOOT0 | §2.2 跳线方案；BOOT0=1 复位后进入系统 ROM Bootloader（AN2606），支持 USB DFU（VID 0483 / PID DF11） |
| 启动注意 | Bootloader 枚举前会探测 USART1（PA9/PA10）等接口电平，这两个 IO 在排针上靠后排列并丝印标注"BOOT 敏感"，外接强上下拉时需留意 |

---

## 5. 调试接口（SWD）

1×6 单排 2.54mm 排针，丝印标注信号名：

| 针 | 信号 | MCU 引脚 |
|---|---|---|
| 1 | 3V3 | — |
| 2 | SWDIO | PA13 |
| 3 | SWCLK | PA14 |
| 4 | SWO | PB3 |
| 5 | NRST | NRST |
| 6 | GND | — |

兼容 ST-LINK / J-Link / DAP-Link，SWO 可做 EventViewer/printf 跟踪。

---

## 6. USB 接口（USB 2.0 Full-Speed Device）

| 项 | 规格 |
|---|---|
| 连接器 | USB-C 16P 母座（仅用 USB2.0 信号组） |
| CC1/CC2 | 各 1×5.1kΩ 下拉到 GND（UFP 角色，缺了则部分主机不供电） |
| VBUS | 4 个 VBUS 引脚并联 → 保险丝 → DCDC；VBUS 检测：68k/100k 分压 → PA9（0Ω/DNP，默认不装，Bootloader 不依赖） |
| D+/D− | PA12/PA11，经 USBLC6-2SC6 ESD 保护，紧邻连接器 |
| DP 上拉 | H743 支持片内 DP 上拉；预留 1.5kΩ（DNP）焊盘应急 |
| 走线 | 差分对等长处理（对内偏差 ≤5mil 即可，FS 速率不敏感）；按嘉立创 4 层阻抗模型算 90Ω 或宽松处理 |

---

## 7. IO 引出、指示与人机

| 项 | 规格 |
|---|---|
| IO 预算 | 共 114 个 GPIO（已核验，含 PC2_C/PC3_C 两个直连 ADC 通道脚，按普通 GPIO 引出）；扣除 PC14/PC15（LSE）、PH0/PH1（HSE）后 110 个，其中 PA13/PA14/PB3 留作 SWD 后约 107 个上排针 |
| 排针 | 两侧长边各 1 条 **2×26 双排 2.54mm**（共 104 孔）：约 96 IO + 每侧首尾 3V3/GND；按端口 PA/PB/PC… 分组排布，丝印标注引脚名 |
| 特殊 IO 标注 | PA13/PA14/PB3（调试复用）、PA9/PA10（Bootloader 探测）、PA11/PA12（USB）在丝印上加 * 号 |
| LED | PWR：3.3V 轨，绿色，1kΩ 限流；USER：PB0，蓝色，1kΩ 限流（低电平点亮） |
| 按键 | USER：PC13，低有效（内部上拉），并联 100nF 去抖 |
| 安装孔 | 4×M3（Ø3.2mm），孔缘离板边 ≥2.5mm，周边 2mm 禁布 |

---

## 8. PCB 叠层与布线规则（写入 DRC 约束）

### 8.1 叠层（嘉立创 4 层 1.6mm 工艺）

| 层 | 用途 |
|---|---|
| L1 | 信号 + 元件（MCU/DCDC/晶振/ESD） |
| L2 | **完整 GND 平面（唯一规则：不分割、不开槽，过孔缝合）** |
| L3 | 电源平面：3.3V 大面积铺铜；5V 在 DCDC 输入侧局部加粗走线（≥0.5mm） |
| L4 | 信号（长距离 IO 走线优先层）+ 底面 GND 铺铜 |

### 8.2 设计规则表（kicad-cli DRC 输入）

| 规则 | 数值 |
|---|---|
| 最小线宽/间距 | 0.15mm / 0.15mm（6/6mil） |
| 过孔 | 孔 0.3mm / 盘 0.6mm |
| 3.3V/5V 电源线 | ≥0.5mm（1A），DCDC PH 开关节点短粗（≥1mm） |
| 一般信号默认线宽 | 0.2mm |
| 去耦电容到引脚 | ≤3mm，每电容 2 个地过孔直下 L2 |
| 晶振区 | 包地 + 缓冲区禁布所有其它网络（含内层） |
| GND 缝合过孔 | 间距 ≤3mm，板缘一圈 |
| USB D+/D− | 同层伴行，对内长度差 ≤1.3mm |
| 铺铜到板边 | ≥0.3mm |
| DRC | 线宽/间距/短路/开路/未连接网络全部为 0 error 才放行 |

### 8.3 自动布线（Freerouting）策略

- 指标：100% 连通率 + DRC 通过；本板无高速等长硬需求，属 Freerouting 舒适区。
- 预布局（脚本生成）：MCU 居中；每颗去耦电容绑定到最近 VDD 引脚；晶振/复位/SWD 紧邻 MCU；USB-C/排针靠边；DCDC 独占一角且 PH 回路面积最小化。
- 布线顺序：GND/电源过孔 → USB 差分（预拉）→ 其余信号。
- 若 Freerouting 多次迭代仍有残线：优先人工规则是放宽 L4 利用率、把 3.3V 改整层、再跑一轮。

本版在自动布线快照上保留了 0.15mm 最小线宽/间距约束，并用可复跑的局部脚本收尾：`fix_usb_clearance.py` 对 USB_DM 做确定性 jog，`merge_vcap_net.py` 将旧版 VCAP1/VCAP2 合并为原理图的 VCAP，`connect_vcap_clusters.py` 在 In2.Cu 板边通道连接两组 VCAP 铜岛。每次补丁后均重新加载板文件并运行 KiCad CLI DRC。

**最终门禁（2026-09-05）**：clearance、shorting_items、tracks_crossing、unconnected_items 均为 0 error；剩余 96 项为装配提示 warning（via_dangling、孔间距、丝印/阻焊及 courtyard），不影响电气连通。

---

## 9. BOM 汇总（数量为规格值，最终以脚本生成为准）

| 类别 | 规格 | 封装 | 数量 |
|---|---|---|---|
| MCU | STM32H743ZIT6 | LQFP144 | 1 |
| DCDC | TPS54331DDAR | SOIC-8(PP) | 1 |
| 电感 | 4.7µH/3A 屏蔽 | 6×6mm | 1 |
| 肖特基 | SS34（1 续流 + 2 输入合路） | SMA | 3 |
| ESD | USBLC6-2SC6 | SOT-23-6 | 1 |
| 自恢复保险丝 | 0.5A | 1206 | 1 |
| 晶振 | 8MHz ±10ppm CL=12pF | 3225 | 1 |
| 晶振 | 32.768kHz ±20ppm CL=12.5pF | 3215 | 1 |
| 磁珠 | 600Ω@100MHz | 0603 | 1 |
| 电容 100nF | X7R 16V（VDD 去耦×N、VREF、DCDC BOOT、NRST 等） | 0402 | ~32 |
| 电容 10µF/22µF/4.7µF/2.2µF/1µF/10nF | X7R（1µF：VDDA、VREF+、VDD33_USB 各一） | 0805/0603/0402 | 2/2/2/2/3/1 |
| 电容 18pF | C0G（晶振负载×4） | 0402 | 4 |
| 电阻 100k/68k/32k/10k/5.1k/1k/100R 系 | 1% | 0402 | 见各节 |
| 电阻 0Ω | VBAT、3.3V 测流 | 0402 | 2 |
| 电阻 1.5k | DP 上拉（DNP） | 0402 | 1 |
| 连接器 | USB-C 16P 母座 | — | 1 |
| 排针 | 2×26 双排 + 1×6 + 1×3 | 2.54mm | 2/1/1 |
| LED | 绿（PWR）+ 蓝（USER） | 0603 | 2 |
| 按键 | 6×6 轻触 | — | 2（NRST、USER） |

> 元件渠道注意：H743 市面翻新片较多，建议立创商城/ST 官方渠道并核对丝印批次与勘误步进。

---

## 10. 测试点与首板验收清单

**测试点（镀锡焊盘）**：5V_VBUS、3V3、GND（×2）、VCAP、NRST、BOOT0、SWDIO、SWCLK、HSE_OUT、LSE_OUT。

| # | 验收项 | 通过标准 |
|---|---|---|
| 1 | 上电前 | 3V3—GND 无短路（R_SEL 0Ω 装上后实测阻抗） |
| 2 | 空载电流 | USB 串电流表，复位态 <50mA |
| 3 | 电源轨 | 3V3=3.30±0.05V，纹波 <30mV；VCAP≈1.1–1.2V |
| 4 | SWD 连接 | CubeProgrammer/DAPLink 读出 IDCODE（H743 DEV_ID=0x450） |
| 5 | 时钟 | RCC 寄存器 HSERDY/LSERDY 置位（或示波器看 OSC） |
| 6 | DFU | BOOT0 跳 3V3 → 复位 → USB 枚举 0483:DF11 |
| 7 | 功能 | 烧录点灯固件，USER LED 闪烁，USER KEY 可中断 |

---

## 11. 风险与待核对项

| 风险 | 缓解 |
|---|---|
| VDD/VCAP/PDR_ON 引脚号手抄错误 | 生成脚本直接读 KiCad 符号库，不人工录入 |
| H743 旧步进 LSE 勘误（ES0392） | 采购新步进；bring-up 清单含 LSE 项 |
| 晶振负载电容与实际晶振不匹配 | 按采购批次规格书复算 C1/C2（§3 公式） |
| USB 差分阻抗 | FS 速率非硬指标；如需 90Ω，用嘉立创阻抗计算器定线宽/间距 |
| Freerouting 残线/绕行 | 预布局 + 多轮迭代；§8.3 降级策略 |
| Bootloader 探测 IO 被外接电平干扰 | §4 排针标注 BOOT 敏感引脚 |

---

## 12. 与自动化实施管线的映射（后续实施时执行）

**实施环境（已验证）**：KiCad 10.0.4，安装于 `C:\Users\27417\AppData\Local\Programs\KiCad\10.0\`（kicad-cli 与自带 Python 3.11.5 均可用）；符号 `MCU_ST_STM32H7:STM32H743ZITx` 与封装 `Package_QFP:LQFP-144_20x20mm_P0.5mm` 均在官方库中确认存在。

本文档即 KiCad 全脚本管线的输入契约：

0. **引脚真源门禁**：`tools/extract_pins.py` 已将 KiCad 符号与 DS12110 引脚图交叉核验（见附录 A），实施脚本以该核验过的符号为唯一引脚真源
1. **原理图生成**（kiutils，读 `STM32H743ZITx` 符号 + 官方封装 `LQFP-144_20x20mm_P0.5mm`）：§2–§7 逐节生成子图与网络 —— **✅ 已完成（2026-09-04）**：`tools/gen_schematic.py` 生成 `kicad/stm32h743_core.kicad_sch`（76 元件 / A2 单页），`tools/check_netlist.py` 网表门禁通过（140 网络逐项断言），PDF 视觉验收通过（汇流排/隐藏 #PWR/分区布局）
2. **网表导出**：`kicad-cli sch export netlist`
3. **预布局生成**：§8.3 放置规则 → 脚本坐标
4. **自动布线**：`kicad-cli pcb export dsn` → Freerouting headless → `kicad-cli pcb import ses`
5. **DRC**：§8.2 规则表 → `kicad-cli pcb drc`，0 error 放行
6. **生产文件**：Gerber + 钻孔 + 坐标 + BOM（可直接投嘉立创 SMT）——已由最终板重新导出至 `kicad/gerbers`、`kicad/pos.csv`、`kicad/bom.csv`
7. **交付**：原理图 PDF + 3D 预览 + 本验收清单执行结果；最终 PCB/原理图/网表位于 `kicad/stm32h743_core.*`

### 12.1 本版交付清单

- PCB：`kicad/stm32h743_core.kicad_pcb`；原理图：`kicad/stm32h743_core.kicad_sch`；网表：`kicad/stm32h743_core.net`
- DRC 报告：`kicad/drc.json`（KiCad 10.0.4，0 error、0 未连接）
- 制造文件：`kicad/gerbers/`（28 个 Gerber/Excellon 文件）、`kicad/pos.csv`、`kicad/bom.csv`
- 预览：`kicad/board_final.png`、`kicad/stm32h743_core.pdf`
- 可复跑补丁：`tools/fix_usb_clearance.py`、`tools/merge_vcap_net.py`、`tools/connect_vcap_clusters.py`

---

## 13. 参考资料

### 13.1 本地参考文件（doc/ 目录，已下载）

| 文件 | 说明 |
|---|---|
| [DS12110_STM32H743xI_数据手册.pdf](doc/DS12110_STM32H743xI_数据手册.pdf) | 数据手册（引脚定义、电气参数、封装） |
| [RM0433_参考手册.pdf](doc/RM0433_参考手册.pdf) | 参考手册（寄存器/RCC/时钟树，bring-up 编程用） |
| [AN4938_硬件开发入门.pdf](doc/AN4938_硬件开发入门.pdf) | 硬件设计首要依据（电源/去耦/时钟/复位） |
| [ES0392_勘误表.pdf](doc/ES0392_勘误表.pdf) | 芯片勘误（已取代旧编号 ES0337；LSE 等条目） |
| [AN2606_系统Bootloader.pdf](doc/AN2606_系统Bootloader.pdf) | 系统 Bootloader 与各接口探测条件（DFU） |
| [TPS54331_数据手册.pdf](doc/TPS54331_数据手册.pdf) | DCDC 典型应用电路 |
| [USBLC6-2SC6_数据手册.pdf](doc/USBLC6-2SC6_数据手册.pdf) | USB ESD 保护 |
| [NUCLEO-H743ZI2_MB1364_官方原理图.pdf](doc/NUCLEO-H743ZI2_MB1364_官方原理图.pdf) | ST 官方同芯片（H743ZI，LQFP144）参考设计，附录 B 对照依据 |
| [WeAct_STM32H7xx_核心板_原理图_V12.pdf](doc/WeAct_STM32H7xx_核心板_原理图_V12.pdf) | 量产开源核心板（H743VIT6）原理图，附录 B 对照依据 |
| [开源参考设计登记.md](doc/开源参考设计登记.md) | 全部参考设计的链接、许可证、复用注意与对照摘要 |

### 13.2 在线参考

- [AN4938 在线版](https://www.st.com/resource/en/application_note/an4938-getting-started-with-stm32h74xig-and-stm32h75xig-mcu-hardware-development-stmicroelectronics.pdf)
- [ES0392 勘误表在线版](https://www.st.com/resource/en/errata_sheet/es0392-stm32h742xig-stm32h743xig-stm32h750xb-stm32h753xi-device-errata-stmicroelectronics.pdf)
- [ST 社区：自定义 H743ZI 板 VCAP/PDR_ON 实战](https://community.st.com/stm32-mcus-boards-and-hardware-tools-26/custom-stm32h743zi-board-wont-connect-failed-to-initialize-dap-164456)
- [DeepBlueMbedded：STM32 VCAP 引脚与电容取值](https://deepbluembedded.com/stm32-vcap-pins-hardware-connection-capacitor-value/)
- [ST 社区：H743ZI DFU 枚举问题](https://community.st.com/stm32-mcus-embedded-software-32/why-stm32h743zi-dfu-bootloader-does-not-come-up-77522)
- [efton.sk STM32 硬件陷阱合集](http://www.efton.sk/STM32/gotcha/gotchas.pdf)

---

## 附录 A：LQFP144 电源/特殊引脚核对表（已核验）

来源：KiCad 符号 `MCU_ST_STM32H7:STM32H743ZITx`（`tools/extract_pins.py` 提取）↔ DS12110 LQFP144 引脚图/引脚表交叉比对。图注可比对的 65 个引脚中 64 个一致（唯一"冲突"pin144 为 PDF 文本粘连伪影，实为 VDD）；pin 95 VDD33USB 由图注上下文三行（96=PC6 / 95=VDD33USB / 94=VSS）直接证实。

| 引脚号 | 名称 | 处理（对应 §2/§4） |
|---|---|---|
| 6 | VBAT | 0Ω 到 3.3V |
| 16 / 38 / 51 / 61 / 83 / 94 / 107 / 120 / 130（共 9） | VSS | 接 GND |
| 17 / 30 / 39 / 52 / 62 / 72 / 84 / 108 / 121 / 131 / 144（共 11） | VDD | 每脚 100nF 就近去耦，汇入 3.3V 主轨 |
| 25 | NRST | 100nF + 按键 + 测试点 |
| 31 / 33 | VSSA / VDDA | 磁珠隔离，1µF + 10nF |
| 32 | VREF+ | 1µF + 100nF，预留外部基准跳线 |
| 71 / 106 | VCAP ×2 | 各 2.2µF 低 ESR（106 号经引脚表行直接证实，71 号经 VCAP 表行与引脚图证实） |
| 95 | VDD33_USB | 3.3V + 1µF + 100nF（USB 域供电，漏接则 USB 不工作）；数据手册引脚表 + Figure 7 + 官方 NUCLEO 板三重证实 |
| 138 | BOOT0 | 100k 下拉 + 3P 跳线 |
| 143 | PDR_ON | 10k 上拉到 VDD |

- GPIO 总数核验：144 − 29 个电源/特殊脚 = **114 个 GPIO**（含 PC2_C=28、PC3_C=29 直连 ADC 通道脚）。
- PDR_ON(143)、BOOT0(138) 为符号库值；图注文本未覆盖到这两脚（周边引脚 137/139/144 等均已核对无误），实施时符号库为真源。

---

## 附录 B：开源参考设计对照（2026-09 检索）

> 各参考设计的链接、许可证与本地文件清单见 [doc/开源参考设计登记.md](doc/开源参考设计登记.md)；WeAct 原理图 PDF 已存 doc/。

检索目的：用已量产验证的设计交叉检验本规格书中"按经验设定"的参数。结论：**无一处分歧需要改设计**，唯一的结构差异（Nucleo 无 HSE 晶振）源于其产品定位不同。

| 参考设计 | 与本设计的对照结论 |
|---|---|
| **ST 官方 NUCLEO-H743ZI2**（MB1364，同芯片同封装，原理图已存 doc/） | VDD33_USB 接 3.3V 域，与本设计 §2.2 一致；VCAP×2 处理一致；BOOT0 经 10k 电阻 + 选择器（本设计 100k 下拉 + 3P 跳线，功能等效）；PDR_ON 处理一致；LSE 用 NX3215SA 32.768kHz（3215 封装），与本设计选型相同；HSE 无晶振——由板载 ST-LINK 的 MCO 馈入 PH0（调试器方案），本设计为独立核心板，保留 8MHz 晶振（DS12110 Figure 71 典型应用即 8MHz 晶振）属正确选择 |
| **WeActStudio/MiniSTM32H7xx**（STM32H743VIT6 核心板，GPL-3.0，GitHub 开源硬件） | 大量产验证的低价核心板：USB-C 供电 + DFU 下载策略与本设计相同；用户键 PC13、BOOT0 按键、2.54 排针引出、四层板——与本设计选型一致 |
| 立创开源平台 H743IIT6 开发板 / H743II 核心板（oshwhub） | LQFP176 项目，电源与最小系统结构与本设计同类，仅作旁证，未引入改动 |

检索中被排除的疑问（记录备查）：

1. "STM32H743BI/BG" 并非新硅片型号——B 是 LQFP208 封装代码（V=100 脚、Z=144 脚、I=176 脚、B=208 脚），数据手册 p2 器件列表可证。
2. DS12110 修订历史显示 LQFP100 引脚图曾把 VDD33USB **改回** VDD，而 LQFP144 的 Figure 7 保留 VDD33USB——即该独立 USB 电源域是 LQFP144/176/208 封装特有（100 脚以下内部供电），不是文档错误。
3. PDF 文本提取两个坑：Nucleo 网络名带下划线（VDD33_USB，搜 "VDD33USB" 搜不到）；DS 引脚表长引脚名被截断（VDD33USB→VDD33US）。已在本项目提取脚本注释中记录。
