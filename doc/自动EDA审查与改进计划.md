# 自动 EDA 审查与改进计划

> 日期：2026-09-05  
> 适用分支：`review/agent-eda-audit-20260905`  
> 目的：把本轮人工复核发现的问题固化为 Agent 可继续执行的设计约束、门禁与待办，避免“DRC 0 error = 设计正确”的误判。

---

## 1. 项目定位与本轮审查原则

本项目的核心目标不是单独做出一块 STM32H743 核心板，而是验证一条 **由 Agent 驱动、可复跑、可审计的自动 EDA 流水线**：

```text
官方数据手册 / 应用笔记 / 勘误
        +
有许可证可追溯的开源参考设计
        ↓
规格书（人审后的设计意图真源）
        ↓
原理图生成
        ↓
独立网表门禁
        ↓
PCB 预布局 / 自动布线
        ↓
DRC / 物理规则 / 设计意图门禁
        ↓
制造文件
        ↓
人工视觉复核 + 首板 bring-up
```

本轮复核继续沿用项目原有的“真源链 + 独立门禁”思想，但增加一条重要原则：

> **独立门禁不仅要验证“生成结果与规格一致”，还必须验证“规格本身与权威资料一致”。**

否则会出现“规格写错 → 生成器忠实执行 → 检查器忠实验证 → 全部 PASS”的自洽错误。

---

## 2. 本轮确认的问题

### P0-1：TPS54331 SS 处理规则错误

当前规格书将 `EN / SS` 一并定义为悬空，`gen_schematic.py` 也不连接 U2.4，`check_netlist.py` 进一步把“U2 的 EN/SS 应悬空”写成门禁。

这不是单点漏画，而是 **错误设计知识贯穿了规格 → 生成 → 验证整条链**。

依据：

- 仓库内：`doc/TPS54331_数据手册.pdf`
- TI TPS54331 Rev.H，Programmable Slow Start Using SS Pin：器件内部没有实现 slow-start 时间，建议在 SS 到 GND 外接电容；推荐 slow-start 1~10 ms，CSS 不超过 27 nF。
- EN 悬空可默认使能，但在 `VIN <= VOUT + 2V` 一类低压差输入条件下，TI 建议考虑外部 UVLO 滞回网络。

建议修复：

1. 规格书改为：`EN` 可悬空默认使能；`SS` 必须外接 CSS。
2. 首版建议 CSS = 10 nF 到 GND，约 4 ms slow-start。
3. `gen_schematic.py` 增加 SS 电容。
4. `check_netlist.py` 改为检查 U2.4 → CSS → GND，U2.3 才允许悬空。
5. 增加“关键器件特殊脚规则”检查表，不能只靠人工记忆。

状态：**本分支仅记录并建立后续门禁方向，原理图改动留给下一轮 Agent 与规格书同步完成。**

---

### P0-2：L2/L3 的“设计意图”没有被自动布线器遵守

规格书定义：

- L1：Signal + Components
- L2：完整 GND plane，不分割、不允许信号穿越
- L3：3.3V Power plane
- L4：Signal

但当前最终 PCB 中，`In1.Cu` 和 `In2.Cu` 都存在大量普通 GPIO / USB 信号线段。

这会造成：

- L2 地平面被 clearance 槽切碎；
- 高速/快速边沿信号回流路径被迫绕行；
- L3 3V3 plane 也被信号切割；
- 即使 clearance / short / unconnected 都是 0，仍然不满足原始叠层设计意图。

**关键结论：传统 DRC 只能证明“几何合法”，不能证明“设计意图合法”。**

建议：

1. 自动布线层策略改成：普通 Signal 仅允许 F.Cu / B.Cu。
2. In1.Cu 只允许 GND；In2.Cu 只允许 +3V3（或明确列出的电源网络）。
3. 增加独立 `layer policy gate`，扫描最终 `.kicad_pcb`，发现普通信号进入 plane layer 直接失败。
4. 对 USB、晶振、时钟等关键网络增加更窄的可用层集合。

状态：**本分支新增层策略门禁脚本；当前旧 PCB 预期会被该门禁拦截。自动布线器层约束调整留给后续 Agent。**

---

### P0-3：85×65 mm 板框与 75×55 mm plane zone 不一致

`gen_pcb.py` / `project_config.py` 的板尺寸是 85×65 mm，但 `finish_pcb.py` 中 zone 顶点被硬编码为 75×55 mm。

结果是内层 GND / 3V3 平面只覆盖左上 75×55 mm 区域，右侧和底部各缺 10 mm。

这属于明确的自动化脚本 bug。

状态：**本分支已修复 `finish_pcb.py`，zone 使用 `project_config.BOARD_W / BOARD_H`，不再硬编码尺寸。**

---

### P0-4：原理图与 PCB parity 没有进入最终放行条件

当前 `pipeline_pcb.py` 的 DRC 退出码只统计：

- `violations`
- `unconnected_items`

没有把 `schematic_parity` 的实质性错误纳入失败条件。

当前 committed `drc.json` 中已经能看到大量 parity warning，其中有两类：

1. **可归一化噪声**：PCB `PD14` vs 原理图 `/PD14`，仅层级前缀不同；
2. **真实不一致**：例如 PCB pad 网络与原理图目标网络不同。

因此不能简单把所有 parity warning 都设为 fatal，而应该做语义归一化后再判断。

状态：**本分支新增 `tools/check_schematic_parity.py`，对 `net_conflict` 做网络名归一化，只对实质不同的网络映射失败。**

后续建议进一步让 PCB 生成器保留 KiCad 层级网络名，减少 parity 噪声。

---

### P1-1：规格、配置、生成脚本之间出现参数真源漂移

当前至少存在：

- 规格书过孔：0.6 / 0.3 mm；
- `project_config.py`：0.6 / 0.3 mm；
- `gen_pcb.py`：0.5 / 0.25 mm；
- 规格书 3.3V / 5V 电源线：>=0.5 mm；
- `pipeline_pcb.py` Power class：0.3 mm。

这对“规格书唯一真源”的工程是不允许的。

建议：

1. 把 fabrication / board / layer policy 参数全部收敛到一个机器可读配置，例如：

```yaml
board:
  width_mm: 85
  height_mm: 65
stackup:
  In1.Cu: plane:GND
  In2.Cu: plane:+3V3
rules:
  clearance_mm: 0.15
  signal_width_mm: 0.20
  via_diameter_mm: 0.60
  via_drill_mm: 0.30
  power_width_mm: 0.50
```

2. Markdown 规格书由该配置生成规则摘要，或反过来从结构化 front matter 读取。
3. `gen_pcb.py`、`pipeline_pcb.py`、DRC gate 都从同一配置读取。
4. CI 增加 `config consistency gate`，禁止重复硬编码关键尺寸。

状态：待后续 Agent 实施。

---

### P1-2：去耦规则写进了规格书，但没有形成物理门禁

规格书要求每个 VDD 100 nF 靠近引脚，距离 <=3 mm，并要求良好的 GND 回路；当前动态布局算法默认把部分去耦中心放在 MCU pad 外约 4~4.5 mm。

建议把“去耦存在”升级成“去耦物理质量”门禁：

- 指定 MCU pin ↔ capacitor ref 的绑定；
- 计算 pad 到 pad 的欧氏距离 / 实际铜路长度；
- 对 VCAP、VDD33_USB、VDDA/VREF 分别设置阈值；
- 检查电容 GND pad 是否在限定半径内至少存在 N 个 GND via；
- 对 VCAP 禁止远端共用电容。

状态：待后续 Agent 实施。

---

## 3. 本分支已执行的改动

### 3.1 `finish_pcb.py`：修复 plane 尺寸硬编码

目标：所有 zone 边界使用统一板尺寸真源，不允许出现 `75×55` 这种历史残留常量。

### 3.2 新增 `tools/check_layer_policy.py`

功能：

- 扫描 `.kicad_pcb` 中所有 segment；
- In1.Cu 仅允许 GND；
- In2.Cu 仅允许 +3V3；
- 发现普通信号进入 plane layer 时退出非 0；
- 输出前若干违规网络与线段坐标，便于 Agent 定位。

该脚本对当前旧 PCB **预期失败**，这是正确行为：它把此前 DRC 看不到的设计意图转成了机器门禁。

### 3.3 新增 `tools/check_schematic_parity.py`

功能：

- 读取 `kicad/drc.json` 的 `schematic_parity`；
- 对 `net_conflict` 提取 PCB net / schematic net；
- 归一化前导 `/`；
- 仅当归一化后仍不同才报错。

目的：把“层级网络名前缀差异”与“真实网表错配”区分开。

---

## 4. 建议的自动门禁矩阵

后续流水线建议不再只有一个总称 DRC，而是显式分层：

| Gate | 输入 | 验证目标 | 失败是否阻断 |
|---|---|---|---|
| Reference gate | datasheet / AN / errata / reference design | 关键规则有权威出处且版本可追溯 | 是 |
| Pin truth gate | KiCad symbol + datasheet pin table | 引脚号/名字/电源域正确 | 是 |
| Schematic net gate | `.net` | 连通性、关键脚、悬空脚规则 | 是 |
| Schematic semantic gate | 规格 + 器件规则 | SS/EN/VCAP/BOOT/USB 等功能性规则 | 是 |
| Footprint gate | symbol + footprint | pin/pad mapping、封装、原点、同名 pad | 是 |
| Placement gate | `.kicad_pcb` | 去耦距离、晶振距离、DCDC 回路、边界 | 是 |
| Layer policy gate | `.kicad_pcb` | plane layer 不被普通信号切割 | 是 |
| Routing gate | `.kicad_pcb` | 线宽、过孔、关键网络层/长度 | 是 |
| KiCad DRC | `.kicad_pcb` | short/clearance/unconnected 等几何规则 | 是 |
| Parity gate | schematic + PCB | 原理图与 PCB 语义一致 | 是 |
| Visual review | PDF / PNG / 3D | 丝印、可制造性、布局合理性 | 首板前是 |
| Bring-up gate | 实板 | 电源、VCAP、时钟、SWD、DFU | 量产前是 |

---

## 5. Agent 后续执行顺序

建议下一轮不要直接“修最终 PCB”，而是按真源向下修：

```text
1. 更新规格书
   ├─ TPS54331 SS
   ├─ EN / UVLO 策略
   ├─ 结构化 stackup / fabrication 参数
   └─ 明确 plane-layer 禁止信号

2. 更新原理图生成器
   └─ SS 外接电容 + 对应器件规则

3. 更新网表门禁
   └─ U2.4 不再允许悬空

4. 更新 PCB 生成 / 自动布线规则
   ├─ F/B only signal routing
   ├─ In1 = GND plane
   ├─ In2 = +3V3 plane
   └─ USB / clock 单独规则

5. 重跑 PCB

6. 运行全部 gate
   ├─ check_netlist
   ├─ check_layer_policy
   ├─ KiCad DRC
   ├─ check_schematic_parity
   └─ placement / decoupling gate（新增）

7. 重新生成 Gerber / Drill / BOM / POS

8. 人工终审
```

**禁止**只修改 `kicad/stm32h743_core.kicad_pcb` 或 Gerber 来“修绿”，因为那会破坏可复跑性。

---

## 6. 对 Agent 工作流的进一步建议

### 6.1 每条关键规则都带 provenance

建议将规则记录成：

```text
rule_id: TPS54331.SS.external_cap
source: doc/TPS54331_数据手册.pdf
section: 7.3.5
requirement: SS must have external capacitor to GND
status: verified
```

生成器与检查器都引用 `rule_id`，而不是各自在注释里写一遍自然语言。

### 6.2 生成器和检查器不能共用同一个“事实表”完成自证

允许共用：

- 文件路径
- 单位换算
- 通用 parser

不建议共用：

- 关键网络期望节点
- 芯片特殊脚行为
- plane layer 使用策略

检查器应该从独立的规则/规格输入得到期望结果。

### 6.3 自动流程必须有“负测试”

每个 gate 至少准备一个故意错误的 fixture：

- 把 VCAP 接错 → net gate 必须失败；
- 把 PD13 放到 In1.Cu → layer policy gate 必须失败；
- 把 PCB R25 pad1 改成 PB0 而 schematic 要 +3V3 → parity gate 必须失败；
- 把 plane 缩成 75×55 → geometry gate 必须失败。

只有能抓住已知错误的检查器，才算有效门禁。

### 6.4 DRC 0 error 的语义必须收窄

后续文档统一使用：

> `KiCad DRC 0 error` = 几何/连接规则通过，不代表电源完整性、回流路径、EMC、器件应用规则或制造可用性全部通过。

最终可投板状态建议定义成：

```text
Reference PASS
+ Schematic PASS
+ Semantic PASS
+ Placement PASS
+ Layer Policy PASS
+ DRC PASS
+ Parity PASS
+ Visual Review PASS
= Prototype Release Candidate
```

---

## 7. 当前阶段结论

这个项目已经证明 Agent 可以把 EDA 的大量机械工作自动化：引脚核验、原理图生成、网表检查、布局、自动布线、DRC、制造文件都能纳入脚本。

本轮暴露出来的主要瓶颈已经不是“Agent 会不会画板”，而是：

1. **设计知识是否可靠；**
2. **设计意图是否能被机器表达；**
3. **检查器是否真的独立；**
4. **传统 DRC 之外是否存在语义/物理质量门禁；**
5. **规格、配置、脚本、产物之间是否始终保持单一真源。**

下一阶段应优先增强这些“工程约束表达和验证能力”，而不是继续增加自动布线复杂度。
