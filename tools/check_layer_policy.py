#!/usr/bin/env python3
"""设计意图门禁：禁止普通信号切割内层 plane。

策略从 project_config.PLANE_POLICY 读取，避免规格/生成器/检查器再次漂移。
该检查针对最终 .kicad_pcb 中的 segment（走线），不替代 KiCad DRC。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from project_config import PCB, PLANE_POLICY  # noqa: E402


def iter_blocks(text: str, head: str):
    """逐个返回形如 `(segment ...)` 的完整 S-expression 块。"""
    token = f"({head}"
    pos = 0
    while True:
        start = text.find(token, pos)
        if start < 0:
            return
        depth = 0
        i = start
        in_string = False
        escaped = False
        while i < len(text):
            ch = text[i]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
            else:
                if ch == '"':
                    in_string = True
                elif ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        yield text[start:i + 1]
                        pos = i + 1
                        break
            i += 1
        else:
            raise ValueError(f"未闭合的 {head} 块 @ offset {start}")


def main() -> int:
    text = PCB.read_text(encoding="utf-8")
    violations = []

    for blk in iter_blocks(text, "segment"):
        lm = re.search(r'\(layer\s+"([^"]+)"\)', blk)
        nm = re.search(r'\(net\s+"([^"]+)"\)', blk)
        if not lm or not nm:
            continue
        layer = lm.group(1)
        net = nm.group(1).lstrip("/")
        allowed = PLANE_POLICY.get(layer)
        if allowed is None or net in allowed:
            continue
        sm = re.search(r'\(start\s+([^\)]+)\)', blk)
        em = re.search(r'\(end\s+([^\)]+)\)', blk)
        violations.append((layer, net, sm.group(1) if sm else "?", em.group(1) if em else "?"))

    if violations:
        print(f"✗ Layer policy gate failed: {len(violations)} signal segments on plane layers")
        for layer, net, start, end in violations[:60]:
            print(f"  - {layer}: {net}  {start} -> {end}")
        if len(violations) > 60:
            print(f"  ... and {len(violations) - 60} more")
        return 2

    print("✓ Layer policy gate passed")
    for layer, nets in PLANE_POLICY.items():
        print(f"  {layer}: only {', '.join(sorted(nets))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
