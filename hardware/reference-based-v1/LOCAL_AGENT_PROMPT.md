# LOCAL_AGENT_PROMPT

复制以下内容给本地 Agent：

---

你正在实现 `changgeruoxiao/hagent` 仓库的 `reference-based-v1` 分支。

先执行：

```bash
git switch reference-based-v1
python hardware/reference-based-v1/local_agent_preflight.py
python hardware/reference-based-v1/gen_v1_schematic_scaffold.py
```

然后完整阅读：

- `hardware/reference-based-v1/LOCAL_AGENT_HANDOFF.md`
- `hardware/reference-based-v1/BASELINE.md`
- `hardware/reference-based-v1/DESIGN_MANIFEST.yaml`
- `hardware/reference-based-v1/PINMAP.md`
- `hardware/reference-based-v1/USB_ARCHITECTURE.md`
- `hardware/reference-based-v1/REFERENCE_MATRIX.md`
- `hardware/reference-based-v1/IMPLEMENTATION.md`

任务：

1. 在 `hardware/reference-based-v1/kicad/` 建立/完善真正可由 KiCad 10 打开的 `h743_dev_v1` 工程。
2. 第一轮只完成 MCU_CORE + POWER + CLOCK_RESET_DEBUG，不要直接做全板 PCB。
3. 复用旧 `tools/sch_build.py` 的文件生成能力可以，但不要复用旧板的自由布线和旧电路决策。
4. 所有关键电路必须交叉检查 datasheet / MB1364 / 相应 PHY datasheet。
5. PB13 固定为 USB_HS_ULPI_D6；Ethernet RMII_TXD1 固定为 PG14。
6. 普通 USB 为 USB-C FS Device；高速 USB 为 USB2 HS 480M、外置 ULPI PHY、USB-A Host；禁止标成 USB 3.0。
7. 每完成一个子系统，运行 Python architecture checks 和 KiCad ERC。
8. 若发现必须改变冻结架构，不要擅自修改；新建/更新 `hardware/reference-based-v1/OPEN_ISSUES.md`，记录证据、候选方案和影响。
9. 不要声称“DRC/ERC=0 即可投板”。

第一阶段交付：

- 可打开的 KiCad 工程
- MCU_CORE + POWER + CLOCK_RESET_DEBUG 原理图
- ERC 报告
- BOM/footprint 暂定清单
- 一次独立自审记录
- Git commit

---
