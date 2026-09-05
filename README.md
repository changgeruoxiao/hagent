# STM32H743ZIT6 核心板 · 全自动 EDA 设计流水线

> 规格书驱动、脚本全自动生成的 STM32H743ZIT6 最小系统核心板：原理图 → PCB 布局布线 → DRC 闭环 → 制造文件，全程无人值守、可复跑。

![board](kicad/board_final.png)

## 项目是什么

一块 **STM32H743ZIT6（LQFP144, Cortex-M7 @ 480MHz）最小系统核心板**，以及生成它的**全自动化 EDA 流水线**：

- 85×65mm 四层板（信号 / GND / 电源 / 信号），USB-C 供电，TPS54331 DCDC，8MHz HSE + 32.768kHz LSE，SWD + USB（DFU），双排 2×28 引出全部 GPIO
- 原理图、PCB、DRC、Gerber 全部由 Python 脚本生成，人工只做规格决策与终审
- 附带一份 [方法论与流程记录](doc/方法论与流程记录.md)，沉淀了全自动 EDA 的完整踩坑经验

## 仓库结构

```
├── STM32H743ZIT6_核心板设计规格书.md   # 唯一真源：设计规格（人审输入）
├── doc/                              # 参考资料与方法论
│   ├── 方法论与流程记录.md            # 五阶段流水线方法论 + 踩坑实录
│   ├── 开源参考设计登记.md            # 参考设计链接/许可证清单
│   ├── extracted/                    # 参考 PDF 的文本提取版
│   └── *.pdf                         # 数据手册/应用笔记/官方原理图
├── kicad/                            # 全部 EDA 产物
│   ├── stm32h743_core.kicad_sch      # 原理图源文件
│   ├── stm32h743_core.kicad_pcb      # PCB 源文件（最终版）
│   ├── stm32h743_core.pdf            # 原理图 PDF
│   ├── board_all_layers.pdf          # PCB 分层图 PDF
│   ├── gerbers/                      # Gerber + Excellon 钻孔（可投板）
│   ├── pos.csv / bom.csv             # 贴片坐标 / 物料清单
│   └── drc.json                      # DRC 报告
└── tools/                            # 全部生成与检查脚本
    ├── extract_pins.py               # 引脚真源核验（符号库 ↔ 数据手册）
    ├── gen_schematic.py              # 原理图生成器
    ├── check_netlist.py              # 网表正确性门禁
    ├── sch_build.py                  # .kicad_sch S-expr 生成框架
    ├── gen_pcb.py                    # PCB 生成器（pcbnew API）
    ├── pipeline_pcb.py               # 布线/回写/DRC/制造文件编排
    └── repair_pcb.py 等              # 局部补线/修复工具
```

## 快速复现

环境：KiCad 10（含自带 Python）、任意 Python 3.10+、Freerouting v2.4.x（获取方式见下）。

```bash
# 1. 原理图生成 + 网表门禁
python tools/gen_schematic.py
python tools/check_netlist.py          # 期望: 网表门禁全部通过

# 2. PCB 建板（含预布线种子）+ DSN 电源类编辑
"<KiCad>/bin/python.exe" tools/gen_pcb.py
python tools/pipeline_pcb.py dsn

# 3. Freerouting 无头布线（-mt 1 必须，见方法论 4.3）
python tools/pipeline_pcb.py route --max-passes 5

# 4. SES 回写 + 整区灌铜 + DRC
"<KiCad>/bin/python.exe" tools/finish_pcb.py
python tools/pipeline_pcb.py drc       # 期望: 0 error / 0 未连通

# 5. 制造文件
python tools/pipeline_pcb.py fab       # Gerber/钻孔 → kicad/gerbers
```

### Freerouting 获取

`tools/freerouting/` 不入库（约 500MB）。手动放置以下内容即可复现：

```bash
mkdir -p tools/freerouting && cd tools/freerouting
# Freerouting v2.4.1（需 Java 25）
curl -L -o freerouting.jar https://github.com/freerouting/freerouting/releases/download/v2.4.1/freerouting-2.4.1.jar
# Temurin JRE 25（国内可用清华镜像）
curl -L -o jre25.zip https://mirrors.tuna.tsinghua.edu.cn/Adoptium/25/jre/x64/windows/OpenJDK25U-jre_x64_windows_hotspot_25.0.4.1_1.zip
unzip jre25.zip
```

## 设计文档

| 文档 | 内容 |
|---|---|
| [设计规格书](STM32H743ZIT6_核心板设计规格书.md) | 电源/时钟/启动/调试/DRC 规则 + 验收清单，自动化流水线的输入契约 |
| [方法论与流程记录](doc/方法论与流程记录.md) | 五阶段流水线、真源链设计、踩坑实录（封装原点/约束错位/种子布线…） |
| [开源参考设计登记](doc/开源参考设计登记.md) | NUCLEO-H743ZI2 / WeAct 等参考设计链接与许可证 |

关键设计依据：ST AN4938（硬件开发入门）、DS12110（数据手册）、ES0392（勘误）、TI TPS54331 数据手册 §8.2 例程——均已本地化在 `doc/`。

## 状态与已知事项

> **CURRENT STATUS: WIP / NOT FAB-READY**
> 层策略整改（审计 P0-2）后信号仅 F/B 两层，Freerouting 未完全收敛（详见 `kicad/build_status.json` 与 `doc/方法论与流程记录.md` §5）。
> 恢复 "Prototype Release Candidate" 状态的条件：`release_gate.py` PASS。

- DRC 当前余量：若干 0.10-0.149mm 间距（高于 JLC 0.127 工艺下限）、若干未连通信号网——明细见 `kicad/build_status.json`
- VCAP1/VCAP2 已在原理图与 PCB 层面统一为 VCAP 网并完成物理连通
- 投板前建议在 KiCad GUI 做一次人工目检（自动化流程的视觉复核无法替代）
- 打样回来后按规格书第 10 节验收清单 bring-up（VCAP 电压、USB DFU 枚举等）

## 许可

代码与设计文件以 [MIT](LICENSE) 发布。`doc/` 内的 ST/TI 版权文档（数据手册/应用笔记/官方原理图）版权归原作者所有，仅作本地参考，请遵循原厂商条款使用。
