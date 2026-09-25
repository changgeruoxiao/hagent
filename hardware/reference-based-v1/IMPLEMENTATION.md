# Reference-Based V1 实施清单

本文档是本分支后续 Agent 的执行顺序。任何 Agent 接手时都先阅读 `hardware/reference-based-v1/BASELINE.md`。

## Phase 0 — 冻结需求

- [x] MCU 固定 STM32H743ZIT6 / LQFP144
- [x] USB 固定 USB FS Device / USB-C
- [x] Ethernet 固定 LAN8742A / RMII / 10-100M
- [x] 不做 USB HS / ULPI
- [x] 不做板载 ST-LINK
- [x] 4 层板
- [x] 保留 GPIO 排针
- [ ] 确认最终板框尺寸
- [ ] 确认 RJ45 方向与 USB-C 相对位置
- [ ] 确认 5V 输入是否只保留 USB-C + 5V 排针

## Phase 1 — 参考设计拆解

逐页提取 MB1364 中以下子系统，并建立“参考网络 → V1 网络”映射：

- [ ] MCU power / VCAP / VDDA / VREF / VDD33_USB
- [ ] NRST / BOOT0 / PDR_ON / VBAT
- [ ] SWD / SWO
- [ ] Ethernet LAN8742A
- [ ] RMII pin map
- [ ] PHY clock
- [ ] PHY strap
- [ ] PHY reset
- [ ] PHY power / decoupling / RBIAS
- [ ] RJ45 / magnetics / LED
- [ ] USB FS
- [ ] USB ESD / VBUS detect

输出：`REFERENCE_MATRIX.md`

## Phase 2 — V1 原理图

建立新的 KiCad 工程，**不要直接修改旧自动生成板**。

建议目录：

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
5. ETHERNET
6. IO_HEADERS

门禁：

- [ ] ERC 通过
- [ ] 与 STM32H743ZIT6 datasheet 引脚表交叉核对
- [ ] 与 MB1364 对应网络逐项 parity check
- [ ] Ethernet 固定引脚没有与其它功能复用冲突
- [ ] USB 固定引脚没有与其它功能复用冲突

## Phase 3 — PCB Floorplan

先布局，不布普通 GPIO：

- [ ] MCU 中央
- [ ] USB-C 靠板边
- [ ] RJ45 靠板边
- [ ] LAN8742A 靠 RJ45
- [ ] PHY 25MHz/REF clock 区域固定
- [ ] HSE/LSE 靠 MCU
- [ ] 去耦与 VCAP 完成
- [ ] 电源热回路完成
- [ ] SWD 靠板边
- [ ] GPIO 排针定位
- [ ] 安装孔定位

输出 floorplan 截图后进行一次人工审查。

## Phase 4 — 关键网络先布

顺序固定：

1. 电源热回路
2. MCU 去耦 / VCAP
3. HSE/LSE
4. Ethernet MDI
5. Ethernet RMII/REF_CLK
6. USB D+/D-
7. SWD
8. 其余 GPIO

关键网络结束后进行第二次审查。

## Phase 5 — 普通信号与自动化

允许 Agent/自动布线器参与：

- GPIO 排针
- LED / KEY
- 低速控制信号

自动化流水线可以复用旧项目的：

- 网表检查思想
- PCB DRC
- 制造文件生成
- BOM/CPL 导出

不能复用“全板自由自动布线”的决策方式。

## Phase 6 — 投板门禁

投板前必须同时具备：

- [ ] ERC 0 error
- [ ] DRC 0 error
- [ ] 0 unconnected
- [ ] BOM 完整
- [ ] footprint 与实物料号一一核验
- [ ] RJ45 footprint 核验
- [ ] USB-C footprint 核验
- [ ] LAN8742A footprint/pin1 核验
- [ ] MCU footprint/pin1 核验
- [ ] Gerber 人工查看
- [ ] Drill 人工查看
- [ ] Board outline 人工查看
- [ ] 铜到板边检查
- [ ] 丝印极性/Pin1 检查
- [ ] 第二人/第二 Agent 独立 schematic audit

## Phase 7 — Bring-up

首板只焊接/验证最小系统后再逐步扩展：

1. 空板短路检查
2. 电源
3. MCU + SWD
4. HSE/LSE
5. USB
6. LAN8742A
7. RJ45
8. GPIO

测试结果记录到 `BRINGUP.md`。