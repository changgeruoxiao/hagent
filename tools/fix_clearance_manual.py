"""Deterministic jogs for the two easy clearance misses.

The original segments were only a few micrometres inside the 0.15 mm rule.
Moving them by a full 0.3--0.4 mm is auditable and leaves the connected
endpoints and the rest of the routed nets unchanged.
"""
from __future__ import annotations

import math
import pathlib
import sys
import pcbnew as p


sys.path.insert(0, str(pathlib.Path(__file__).parent))
from project_config import PCB


def mm(v): return p.FromMM(v)
def vec(xy): return p.VECTOR2I(mm(xy[0]), mm(xy[1]))


def find(board, net, a, b, layer):
    for t in list(board.GetTracks()):
        if t.Type() == p.PCB_VIA_T or t.GetLayer() != layer or t.GetNetname().lstrip("/") != net:
            continue
        q = {(round(t.GetStart().x/1e6, 4), round(t.GetStart().y/1e6, 4)),
             (round(t.GetEnd().x/1e6, 4), round(t.GetEnd().y/1e6, 4))}
        if q == {(round(a[0], 4), round(a[1], 4)), (round(b[0], 4), round(b[1], 4))}:
            return t
    raise RuntimeError(f"missing segment {net} {a}->{b}")


def add(board, net, points, layer):
    ni = board.FindNet(net)
    for a, b in zip(points, points[1:]):
        if math.dist(a, b) < 1e-5: continue
        t = p.PCB_TRACK(board); t.SetStart(vec(a)); t.SetEnd(vec(b))
        t.SetLayer(layer); t.SetWidth(mm(.2)); t.SetNet(ni); t.SetLocked(True); board.Add(t)


def main():
    b = p.LoadBoard(str(PCB))
    # PD10: pull the long front segment away from the nearby GND via.  Mutate
    # the existing segment in place so KiCad's SWIG track collection remains
    # valid while the two jog segments are added.
    pd10 = find(b, "PD10", (53.2221, 38.3096), (57.5606, 38.3096), p.F_Cu)
    pd10.SetEnd(vec((54.20, 38.3096)))
    add(b, "PD10", [(53.2221, 38.3096), (54.20, 38.3096),
                     (54.20, 39.80), (57.5606, 39.80),
                     (57.5606, 38.3096)], p.F_Cu)
    # PC6: leave the QFP pad horizontally before turning toward its via.
    pc6a = find(b, "PC6", (53.1625, 29.75), (53.2886, 29.6239), p.F_Cu)
    pc6b = find(b, "PC6", (53.2886, 29.6239), (54.3077, 29.6239), p.F_Cu)
    pc6a.SetEnd(vec((53.55, 29.75)))
    pc6b.SetStart(vec((54.0, 29.75)))
    add(b, "PC6", [(53.55, 29.75), (54.0, 29.75),
                    (54.0, 29.75), (54.3077, 29.6239)], p.F_Cu)
    filler = p.ZONE_FILLER(b); filler.Fill(list(b.Zones()))
    p.SaveBoard(str(PCB), b)


if __name__ == "__main__": main()
