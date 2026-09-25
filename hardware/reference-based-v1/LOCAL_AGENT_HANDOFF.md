# 本地 Agent 交接说明 — H743 Reference-Based V1

> 目标分支：`reference-based-v1`
>
> 本文档是本地 Codex / Claude Code / OpenCode / 其他 coding agent 接手 KiCad 实现时的入口文档。

## 0. 先说结论

下一阶段必须在**本地 KiCad 环境**完成。

原因：

- GitHub 侧可以维护文档、规格、Python 生成器和检查脚本；
- 但真正打开/保存 KiCad 工程、运行 `kicad-cli` ERC/DRC、调用 KiCad 自带 Python/`pcbnew`、查看布局和 3D/制造输出，最好在本机执行；
- 这块板包含 RMII、USB2 HS/ULPI、USB 差分、电源，不能只凭文本生成结果直接投板。

本地 Agent 的任务不是“重新设计”，而是**按照冻结架构把成熟参考设计迁移成 KiCad 工程，并持续运行自动门禁**。

---

## 1. 必须先读的文件

按顺序：

1. `hardware/reference-based-v1/BASELINE.md`
2. `hardware/reference-based-v1/DESIGN_MANIFEST.yaml`
3. `hardware/reference-based-v1/PINMAP.md`
4. `hardware/reference-based-v1/USB_ARCHITECTURE.md`
5. `hardware/reference-based-v1/REFERENCE_MATRIX.md`
6. `hardware/reference-based-v1/IMPLEMENTATION.md`

参考资料：

- `doc/DS12110_STM32H743xI_数据手册.pdf`
- `doc/RM0433_参考手册.pdf`
- `doc/AN4938_硬件开发入门.pdf`
- `doc/ES0392_勘误表.pdf`
- `doc/NUCLEO-H743ZI2_MB1364_官方原理图.pdf`
- `doc/WeAct_STM32H7xx_核心板_原理图_V12.pdf`

旧自动板代码可以参考“工具实现”，不能作为新板电路真源：

- `tools/sch_build.py`
- `tools/gen_schematic.py`
- `tools/check_netlist.py`
- `tools/gen_pcb.py`
- `tools/pipeline_pcb.py`

---

## 2. 本地环境

建议：

- KiCad 10.x
- Python 3.10+
- Git
- Windows 可直接安装 KiCad；WSL 仅用于文本/脚本辅助，不建议用 WSL 直接驱动 Windows KiCad GUI

先运行：

```bash
python hardware/reference-based-v1/local_agent_preflight.py
```

预期：

- 找到 Python
- 找到 `kicad-cli`
- 架构 manifest 检查通过
- pin reservation 检查通过
- 新 KiCad 工作目录存在

如果 `kicad-cli` 没加入 PATH，Windows 常见路径类似：

```text
C:\Program Files\KiCad\10.0\bin\kicad-cli.exe
```

可以把其目录加入 PATH，或者设置：

```powershell
$env:KICAD_CLI="C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
```

---

## 3. 先生成 V1 MCU 原理图骨架

运行：

```bash
python hardware/reference-based-v1/gen_v1_schematic_scaffold.py
```

输出：

```text
hardware/reference-based-v1/kicad/h743_dev_v1.kicad_sch
```

这个脚本只完成：

- 放置 STM32H743ZIT6
- 电源/特殊引脚基础网络
- 冻结的 Ethernet RMII 引脚
- USB FS 引脚
- USB HS ULPI 引脚
- SWD / HSE / LSE
- pin conflict 自检

**它不是完整原理图。**

本地 Agent 接下来必须继续画：

1. POWER
2. CLOCK_RESET_DEBUG
3. USB_FS
4. USB_HS_ULPI
5. ETHERNET
6. IO_HEADERS

---

## 4. 本地 Agent 的实际执行顺序

### Step A — 建立可打开的 KiCad 工程

在：

```text
hardware/reference-based-v1/kicad/
```

创建/维护：

- `h743_dev_v1.kicad_pro`
- `h743_dev_v1.kicad_sch`
- `h743_dev_v1.kicad_pcb`

可以让 scaffold 脚本先生成 `.kicad_sch`，然后用 KiCad GUI 打开并保存一次，让 KiCad 自己补齐项目元数据。

### Step B — MCU / Power 最小系统

先完成并检查：

- 所有 VDD/VSS
- VDD33_USB
- VDDA/VREF
- VCAP1/VCAP2
- VBAT
- PDR_ON
- NRST
- BOOT0
- HSE/LSE
- SWD

不要先画 Ethernet/USB 再回头补 MCU 电源。

### Step C — USB FS

实现：

- USB-C Device/UFP
- PA11 / PA12
- CC1/CC2 Rd
- ESD
- VBUS sense
- DFU/CDC 使用场景

### Step D — USB HS / ULPI

实现：

- USB3320C / USB3300 类 PHY
- PA3/PA5/PB0/PB1/PB10/PB11/PB12/PB13/PB5/PC0/PC2/PC3
- PHY power / clock / RBIAS / RESETB
- USB-A Host
- 5V current-limited high-side switch
- over-current feedback
- ESD

注意：

- PB13 = ULPI_D6
- Ethernet TXD1 = PG14
- **禁止**把 Ethernet TXD1 改回 PB13

### Step E — Ethernet

实现：

- LAN8742A
- PA1/PA2/PC1/PA7/PC4/PC5/PG11/PG13/PG14
- strap
- RBIAS
- reset
- clock
- magnetics / RJ45
- LED

### Step F — PCB

先 floorplan，再关键网络，再普通 GPIO。

禁止先跑全板 autorouter。

---

## 5. 每次修改后的检查

至少运行：

```bash
python hardware/reference-based-v1/local_agent_preflight.py
```

原理图存在后再运行：

```bash
kicad-cli sch erc hardware/reference-based-v1/kicad/h743_dev_v1.kicad_sch
```

PCB 存在后：

```bash
kicad-cli pcb drc hardware/reference-based-v1/kicad/h743_dev_v1.kicad_pcb
```

具体 KiCad 10 CLI 参数如本机版本有差异，以：

```bash
kicad-cli sch erc --help
kicad-cli pcb drc --help
```

为准。

---

## 6. Agent 不能自行修改的冻结项

- MCU: STM32H743ZIT6 / LQFP144
- Ethernet PHY: LAN8742A
- Ethernet mode: RMII
- RMII TXD1: PG14
- USB FS: PA11/PA12
- USB HS: ULPI
- ULPI D6: PB13
- USB HS 电气速率：USB2 High-Speed 480 Mbit/s，不是 USB3
- L2：完整 GND
- USB HS Host VBUS：必须有限流电源开关

如果发现上述架构不可实现，不允许静默改设计；必须写入 `OPEN_ISSUES.md` 并提交证据。

---

## 7. 推荐提交粒度

不要一次提交“整板完成”。

推荐：

1. `feat(hw): scaffold H743 MCU core`
2. `feat(hw): complete power clock reset debug`
3. `feat(hw): add USB FS device port`
4. `feat(hw): add ULPI USB HS host`
5. `feat(hw): add LAN8742A RMII ethernet`
6. `feat(hw): add IO headers and schematic checks`
7. `feat(hw): add PCB floorplan`
8. `feat(hw): route critical nets`
9. `feat(hw): finish PCB and manufacturing gate`

每个阶段都保留可审查状态。

---

## 8. 给本地 Agent 的启动指令

可以直接把下面这段给本地 Agent：

> 当前仓库分支为 `reference-based-v1`。先阅读 `hardware/reference-based-v1/LOCAL_AGENT_HANDOFF.md` 以及其中列出的所有规格文件。不要修改冻结架构。先运行 `local_agent_preflight.py`，再运行 `gen_v1_schematic_scaffold.py` 创建 MCU 原理图骨架。随后按 IMPLEMENTATION.md 的 Phase 2 顺序完成 MCU core/power/clock/reset/debug，运行 KiCad ERC 后提交。不要提前进行 PCB 全板布线，不要把 PB13 分配给 Ethernet，PB13 固定为 ULPI_D6，Ethernet RMII_TXD1 固定 PG14。
