#!/usr/bin/env python3
"""统一搜索式补线路由器 v12(须用 KiCad python)。

对 DRC 未连通项在 In2 层做候选走廊搜索:
  族1: a → (xv,a.y) → (xv,yh) → (b.x,yh) → b
  族2: a → (a.x,yh) → (xv,yh) → (xv,b.y) → b
避障: 其它网 In2 走线段 + 全层过孔/THT 焊盘(SMD 不挡内层);
锚点 1.3mm 逃逸豁免(QFP 犬骨天然成立)。落地后 Solid 重灌铜。
"""
import json
import sys
import math
import re
from pathlib import Path

import pcbnew
sys.path.insert(0, str(Path(__file__).parent))
from project_config import PCB, OUT

WS = Path(__file__).resolve().parents[1]
PCB = PCB
DRC = OUT / "drc.json"

CLEAR_NM = pcbnew.FromMM(0.18)
ESCAPE_NM = pcbnew.FromMM(1.3)
XVS = [12, 14, 16, 18, 20, 22, 24, 26.5, 29.5, 33, 36, 39, 42, 45, 56, 58, 60, 62, 65, 68, 71, 74, 77, 81]
YHS = [1.5, 3.2, 5.5, 7, 9, 11, 13, 24, 26, 28, 36, 39, 47, 49.5, 52, 54.5, 57, 59.5, 62]


def out(*a):
    print(*a, flush=True)


def collect_obstacles(board, net_name):
    """soft 障碍(GND In2 冗余段, 可删); 硬障碍: 过孔/THT/非 GND 段。"""
    soft, hard = [], []
    for f in board.GetFootprints():
        for p in f.Pads():
            if p.GetNetname() == net_name:
                continue
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
                continue
            pos = p.GetPosition()
            hard.append(("pt", pos.x, pos.y, max(p.GetSize().x, p.GetSize().y) / 2))
    for t in board.GetTracks():
        if t.GetNetname() == net_name:
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            pos = t.GetPosition()
            hard.append(("pt", pos.x, pos.y, pcbnew.FromMM(0.25)))
        elif t.GetLayer() == pcbnew.In2_Cu:
            s, e = t.GetStart(), t.GetEnd()
            if t.GetNetname() == "GND":
                soft.append(("seg", s.x, s.y, e.x, e.y, pcbnew.FromMM(0.1)))
            else:
                hard.append(("seg", s.x, s.y, e.x, e.y, pcbnew.FromMM(0.1)))
    return hard, soft


def pt_seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    ll = dx * dx + dy * dy
    t0 = 0 if ll == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / ll))
    return math.hypot(px - (x1 + t0 * dx), py - (y1 + t0 * dy))


def seg_clear(pts_nm, obs, anchors_nm):
    for i in range(len(pts_nm) - 1):
        x1, y1 = pts_nm[i]
        x2, y2 = pts_nm[i + 1]
        steps = max(2, int(math.hypot(x2 - x1, y2 - y1) / pcbnew.FromMM(0.25)) + 1)
        for s in range(steps + 1):
            t = s / steps
            px = x1 + (x2 - x1) * t
            py = y1 + (y2 - y1) * t
            for o in obs:
                if o[0] == "pt":
                    _, ox, oy, orr = o
                    if any(math.hypot(ox - ax, oy - ay) < ESCAPE_NM for ax, ay in anchors_nm):
                        continue
                    if math.hypot(ox - px, oy - py) < orr + CLEAR_NM:
                        return False
                else:
                    _, x1o, y1o, x2o, y2o, orr = o
                    if any(pt_seg_dist(ax, ay, x1o, y1o, x2o, y2o) < ESCAPE_NM for ax, ay in anchors_nm):
                        continue
                    if pt_seg_dist(px, py, x1o, y1o, x2o, y2o) < orr + CLEAR_NM:
                        return False
    return True


def main():
    board = pcbnew.LoadBoard(str(PCB))
    rep = json.loads(DRC.read_text(encoding="utf-8"))

    def fp(ref):
        return next(f for f in board.GetFootprints() if f.GetReference() == ref)

    done = 0
    for u in rep.get("unconnected_items", []):
        items = u.get("items", [])
        if len(items) < 2:
            continue
        net_name, anchors, kinds = None, [], []
        ok = True
        for it in items:
            desc = it.get("description", "")
            m = re.search(r"\[([^\]]+)\]", desc)
            if m:
                net_name = m.group(1)
            mp = re.search(r"(\S+) 的(?:PTH )?焊盘 (\S+)", desc)
            mt = re.search(r"走线 \[([^\]]+)\]", desc)
            pos = it.get("pos") or {}
            px, py = pcbnew.FromMM(pos.get("x", 0)), pcbnew.FromMM(pos.get("y", 0))
            if mp:
                try:
                    pad = fp(mp.group(1)).FindPadByNumber(mp.group(2))
                except StopIteration:
                    ok = False
                    break
                anchors.append(pad.GetPosition())
                kinds.append("smd" if pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD else "tht")
            elif mt:
                best, bd = None, 1e18
                for t in board.GetTracks():
                    if t.Type() != pcbnew.PCB_VIA_T and t.GetNetname() == m.group(1):
                        for e in (t.GetStart(), t.GetEnd()):
                            d = math.hypot((e.x - px) / 1e6, (e.y - py) / 1e6)
                            if d < bd:
                                bd, best = d, e
                if best is None or bd > pcbnew.FromMM(3.0):
                    ok = False
                    break
                anchors.append(best)
                kinds.append("track")
            else:
                ok = False
                break
        if not ok or net_name is None or len(anchors) != 2:
            print(f"  {net_name}: 解析失败, 跳过")
            continue
        net = None
        for f in board.GetFootprints():
            for p in f.Pads():
                if p.GetNetname() == net_name:
                    net = p.GetNet()
                    break
        hard, soft = collect_obstacles(board, net_name)
        obs = hard + soft
        soft_del = []
        A = (anchors[0].x, anchors[0].y)
        B = (anchors[1].x, anchors[1].y)
        AX, AY = anchors[0].x / 1e6, anchors[0].y / 1e6
        BX, BY = anchors[1].x / 1e6, anchors[1].y / 1e6
        chosen = None
        def seg_clear_full(c):
            return seg_clear(c, obs, [A, B]) and seg_clear(c, hard, [A, B])
        for xv in XVS:
            for yh in YHS:
                c1 = [A, (pcbnew.FromMM(xv), A[1]), (pcbnew.FromMM(xv), pcbnew.FromMM(yh)),
                      (B[0], pcbnew.FromMM(yh)), B]
                if seg_clear(c1, obs, [A, B]):
                    chosen = (c1, f"x{xv}/y{yh}")
                    break
                c2 = [A, (A[0], pcbnew.FromMM(yh)), (pcbnew.FromMM(xv), pcbnew.FromMM(yh)),
                      (pcbnew.FromMM(xv), B[1]), B]
                if seg_clear(c2, obs, [A, B]):
                    chosen = (c2, f"y{yh}/x{xv}")
                    break
            if chosen:
                break
        if chosen is None:
            print(f"  {net_name}: 搜索失败, 需人工处理")
            continue
        # 落地前: 删除路径压到的 GND 冗余段
        for i in range(len(chosen) - 1):
            x1, y1 = chosen[i]
            x2, y2 = chosen[i + 1]
            steps = max(2, int(math.hypot(x2 - x1, y2 - y1) / pcbnew.FromMM(0.25)) + 1)
            for s in range(steps + 1):
                t = s / steps
                px = x1 + (x2 - x1) * t
                py = y1 + (y2 - y1) * t
                for o in soft:
                    _, x1o, y1o, x2o, y2o, orr = o
                    if pt_seg_dist(px, py, x1o, y1o, x2o, y2o) < orr + pcbnew.FromMM(0.18):
                        tgt = None
                        for tt in board.GetTracks():
                            if (tt.GetLayer() == pcbnew.In2_Cu and tt.GetNetname() == "GND"
                                    and pt_seg_dist(px, py, tt.GetStart().x, tt.GetStart().y,
                                                    tt.GetEnd().x, tt.GetEnd().y) < pcbnew.FromMM(0.05)):
                                tgt = tt
                                break
                        if tgt is not None:
                            board.Remove(tgt)
                            soft = [oo for oo in soft if not (oo[0] == "seg" and
                                    abs(oo[1] - tt.GetStart().x) < 100 and abs(oo[2] - tt.GetStart().y) < 100)]
                        break
        cand, tag = chosen
        for (pos, kind) in zip((cand[0], cand[-1]), kinds):
            if kind == "smd":
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(pcbnew.VECTOR2I(int(pos[0]), int(pos[1])))
                v.SetViaType(pcbnew.VIATYPE_THROUGH)
                v.SetWidth(pcbnew.FromMM(0.5))
                v.SetDrill(pcbnew.FromMM(0.25))
                v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                v.SetNet(net)
                board.Add(v)
        prev = None
        for pos in cand:
            pt = pcbnew.VECTOR2I(int(pos[0]), int(pos[1]))
            if prev is not None:
                tr = pcbnew.PCB_TRACK(board)
                tr.SetStart(prev)
                tr.SetEnd(pt)
                tr.SetWidth(pcbnew.FromMM(0.2))
                tr.SetLayer(pcbnew.In2_Cu)
                tr.SetNet(net)
                board.Add(tr)
            prev = pt
        done += 1
        out(f"  补线 {net_name}: 走廊 {tag}, {len(cand)-1} 段 In2")
    out(f"共补线 {done} 条")

    full = getattr(pcbnew, "ZONE_CONNECTION_FULL", 2)
    for z in board.Zones():
        z.SetPadConnection(full)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(list(board.Zones()))
    pcbnew.SaveBoard(str(PCB), board)
    out("已保存(含重灌铜)")


if __name__ == "__main__":
    main()
