#!/usr/bin/env python3
"""语义化原理图/PCB parity 门禁。

KiCad schematic_parity 中会把 PCB net `PD14` 与 schematic net `/PD14`
报告为 warning。这里先归一化层级前导 `/`，仅把实质性的 net_conflict 作为失败。

注意：此脚本读取现有 kicad/drc.json；应在 kicad-cli pcb drc --schematic-parity 之后运行。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from project_config import OUT  # noqa: E402

DRC = OUT / "drc.json"
NET_CONFLICT = re.compile(r"焊盘网络 \((.*?)\) 与原理图 \((.*?)\) 指定的网络不匹配")


def norm_net(name: str) -> str:
    return name.strip().lstrip("/")


def main() -> int:
    if not DRC.exists():
        print(f"✗ parity gate: missing {DRC}; run KiCad DRC with --schematic-parity first")
        return 2

    data = json.loads(DRC.read_text(encoding="utf-8"))
    parity = data.get("schematic_parity", [])
    real_conflicts = []
    normalized_noise = 0

    for item in parity:
        if item.get("type") != "net_conflict":
            continue
        desc = item.get("description", "")
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
    print(f"normalized hierarchical-name noise: {normalized_noise}")

    if real_conflicts:
        print(f"✗ Semantic parity gate failed: {len(real_conflicts)} real net conflicts")
        for pcb_net, sch_net, desc, items in real_conflicts[:40]:
            loc = ""
            if items:
                first = items[0]
                loc = f" | {first.get('description', '')} @ {first.get('pos', '')}"
            print(f"  - PCB={pcb_net} schematic={sch_net}: {desc}{loc}")
        if len(real_conflicts) > 40:
            print(f"  ... and {len(real_conflicts) - 40} more")
        return 2

    print("✓ Semantic parity gate passed (no real net_conflict after normalization)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
