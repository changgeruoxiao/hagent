#!/usr/bin/env python3
"""语义化原理图/PCB parity 门禁。

目标：过滤 KiCad 层级网名噪声，但对真正的原理图/PCB 漂移 fail closed。
当前阻断：
- 实质性 net_conflict；
- schematic 中存在而 PCB 缺失的 footprint。

注意：此脚本读取现有 kicad/drc.json；应在
`kicad-cli pcb drc --schematic-parity` 之后运行。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from project_config import DRC  # noqa: E402

NET_CONFLICT = re.compile(r"焊盘网络 \((.*?)\) 与原理图 \((.*?)\) 指定的网络不匹配")
FATAL_PARITY_TYPES = {"missing_footprint"}


def norm_net(name: str) -> str:
    name = name.strip().lstrip("/")
    # KiCad 可把原理图明确 No Connect 表示为 unconnected-(...)，
    # PCB 侧则显示 <no net>；二者都表示“无逻辑网络”。
    if name == "<no net>" or name.startswith("unconnected-"):
        return "<UNCONNECTED>"
    return name


def main() -> int:
    if not DRC.exists():
        print(f"✗ parity gate: missing {DRC}; run KiCad DRC with --schematic-parity first")
        return 2

    data = json.loads(DRC.read_text(encoding="utf-8"))
    parity = data.get("schematic_parity", [])
    real_conflicts = []
    fatal_entries = []
    normalized_noise = 0

    for item in parity:
        typ = item.get("type")
        desc = item.get("description", "")

        if typ in FATAL_PARITY_TYPES:
            fatal_entries.append(item)
            continue
        if typ != "net_conflict":
            continue

        m = NET_CONFLICT.search(desc)
        if not m:
            # 无法可靠解释的 net_conflict 不能静默放过。
            real_conflicts.append(("?", "?", desc, item.get("items", [])))
            continue
        pcb_net, sch_net = m.groups()
        if norm_net(pcb_net) == norm_net(sch_net):
            normalized_noise += 1
            continue
        real_conflicts.append((pcb_net, sch_net, desc, item.get("items", [])))

    print(f"schematic_parity entries: {len(parity)}")
    print(f"normalized net-name/no-connect noise: {normalized_noise}")

    total_fatal = len(real_conflicts) + len(fatal_entries)
    if total_fatal:
        print(f"✗ Semantic parity gate failed: {total_fatal} blocking entries")
        for pcb_net, sch_net, desc, items in real_conflicts[:30]:
            loc = ""
            if items:
                first = items[0]
                loc = f" | {first.get('description', '')} @ {first.get('pos', '')}"
            print(f"  - net_conflict PCB={pcb_net} schematic={sch_net}: {desc}{loc}")
        for item in fatal_entries[:30]:
            print(f"  - {item.get('type')}: {item.get('description', '')}")
        return 2

    print("✓ Semantic parity gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
