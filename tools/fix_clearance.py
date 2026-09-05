"""Repair the five measured clearance misses in the legacy routed candidate.

Only the offending copper segments are replaced.  Each replacement is
proposed by the same geometry-aware router and checked against exact KiCad
shapes before it is saved; the rest of the routed board is left untouched.
"""
from __future__ import annotations

import math
import pathlib
import sys

import pcbnew as p

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from local_router import route, exact_clear
from project_config import PCB


def mm(v): return p.FromMM(v)
def vec(xy): return p.VECTOR2I(mm(xy[0]), mm(xy[1]))


def find_net(board, name):
    info = board.GetNetInfo()
    # GetNetInfo() is a NETINFO_LIST in KiCad 10; use the board-level count
    # because older Python bindings sometimes expose the list proxy lazily.
    return next(info.GetNetItem(i) for i in range(board.GetNetCount())
                if info.GetNetItem(i).GetNetname().lstrip("/") == name)


def endpoint(t):
    return ((t.GetStart().x / 1e6, t.GetStart().y / 1e6),
            (t.GetEnd().x / 1e6, t.GetEnd().y / 1e6))


def same_segment(t, net, a, b, layer):
    if t.Type() == p.PCB_VIA_T or t.GetNetname().lstrip("/") != net or t.GetLayer() != layer:
        return False
    x, y = endpoint(t)
    return ({(round(x[0], 4), round(x[1], 4)), (round(y[0], 4), round(y[1], 4))}
            == {(round(a[0], 4), round(a[1], 4)), (round(b[0], 4), round(b[1], 4))})


def remove_segment(board, net, a, b, layer):
    for t in list(board.GetTracks()):
        if same_segment(t, net, a, b, layer):
            board.Remove(t)
            return
    raise RuntimeError(f"segment not found: {net} {a}->{b}")


def add_path(board, net, path, layer, width=0.2, net_item=None):
    ni = net_item or find_net(board, net)
    for a, b in zip(path, path[1:]):
        if math.dist(a, b) < 1e-5: continue
        t = p.PCB_TRACK(board)
        t.SetStart(vec(a)); t.SetEnd(vec(b)); t.SetLayer(layer)
        t.SetWidth(mm(width)); t.SetNet(ni); t.SetLocked(True); board.Add(t)


def replace_track(board, net, start, end, layer=p.F_Cu):
    ni = find_net(board, net)
    remove_segment(board, net, start, end, layer)
    path = route(board, ni.GetNetCode(), start, end, 0.2, layer, 8.0, 0.1)
    if path is None or not exact_clear(board, path, ni.GetNetCode(), layer, 0.2, 0.15):
        raise RuntimeError(f"no exact replacement for {net}")
    add_path(board, net, path, layer, net_item=ni)
    print(f"{net}: replaced {len(path)-1} {board.GetLayerName(layer)} segments", flush=True)


def replace_pc6(board):
    # Remove the two short front fanout segments, retaining the existing PC6
    # via and its inner-layer continuation.
    ni = find_net(board, "PC6")
    remove_segment(board, "PC6", (53.1625, 29.75), (53.2886, 29.6239), p.F_Cu)
    remove_segment(board, "PC6", (53.2886, 29.6239), (54.3077, 29.6239), p.F_Cu)
    path = route(board, ni.GetNetCode(), (53.1625, 29.75), (54.3077, 29.6239),
                 0.2, p.F_Cu, 8.0, 0.1)
    if path is None or not exact_clear(board, path, ni.GetNetCode(), p.F_Cu, 0.2, 0.15):
        raise RuntimeError("no exact replacement for PC6")
    add_path(board, "PC6", path, p.F_Cu, net_item=ni)
    print(f"PC6: replaced fanout with {len(path)-1} F.Cu segments", flush=True)


def main():
    board = p.LoadBoard(str(PCB))
    replace_track(board, "PD10", (53.2221, 38.3096), (57.5606, 38.3096))
    replace_pc6(board)
    filler = p.ZONE_FILLER(board)
    filler.Fill(list(board.Zones()))
    p.SaveBoard(str(PCB), board)


if __name__ == "__main__": main()
