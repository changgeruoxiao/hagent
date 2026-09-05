#!/usr/bin/env python3
"""布局批量预检(须用 KiCad python): 按 PLACE 加载封装旋转定位, 两两焊盘包围盒比对。"""
import sys
from pathlib import Path

import pcbnew

sys.path.insert(0, str(Path(__file__).parent))
import gen_pcb  # noqa: E402

FP_DIR = gen_pcb.FP_DIR


def bbox_of(fp_id, x, y, angle):
    lib, name = fp_id.split(":")
    fp = pcbnew.FootprintLoad(str(FP_DIR / f"{lib}.pretty"), name)
    fp.SetPosition(pcbnew.VECTOR2I(gen_pcb.mm(x), gen_pcb.mm(y)))
    fp.SetOrientationDegrees(angle)
    pads = list(fp.Pads())
    pts = []
    for p in pads:
        r = max(p.GetSize().x, p.GetSize().y) / 2
        cx, cy = p.GetPosition().x, p.GetPosition().y
        pts += [(cx - r, cy - r), (cx + r, cy + r)]
    if not pts:
        return None
    bcx = (min(x for x, _ in pts) + max(x for x, _ in pts)) / 2
    bcy = (min(y for _, y in pts) + max(y for _, y in pts)) / 2
    tx, ty = gen_pcb.mm(x), gen_pcb.mm(y)
    pts = [(px + tx - bcx, py + ty - bcy) for px, py in pts]
    m = gen_pcb.mm(0.15)
    return ((min(x for x, _ in pts) - m) / 1e6, (min(y for _, y in pts) - m) / 1e6,
            (max(x for x, _ in pts) + m) / 1e6, (max(y for _, y in pts) + m) / 1e6)


def main():
    comps, _ = gen_pcb.parse_netlist()
    boxes = {}
    for ref, (x, y, ang) in gen_pcb.PLACE.items():
        bb = bbox_of(comps[ref][1], x, y, ang)
        if bb:
            boxes[ref] = bb
    refs = list(boxes)
    bad = 0
    for i in range(len(refs)):
        for j in range(i + 1, len(refs)):
            if gen_pcb.bbox_hit(boxes[refs[i]], boxes[refs[j]]):
                print(f"重叠: {refs[i]}{boxes[refs[i]]} <-> {refs[j]}{boxes[refs[j]]}")
                bad += 1
    print(f"预检: {'通过' if bad == 0 else f'{bad} 处重叠'}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
