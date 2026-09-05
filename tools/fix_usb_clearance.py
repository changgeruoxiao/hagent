"""Move the USB_DM front-layer segment clear of adjacent vias.

The original horizontal segment was just below the 0.15 mm copper clearance
rule at the USB_DP and PA10 vias.  This keeps the two via endpoints fixed and
adds a short downward jog on F.Cu, leaving the controlled-impedance inner
layer route unchanged.
"""
from __future__ import annotations

import math
import pathlib
import sys

import pcbnew as p

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from project_config import PCB


def mm(v: float) -> int:
    return p.FromMM(v)


def vec(xy: tuple[float, float]):
    return p.VECTOR2I(mm(xy[0]), mm(xy[1]))


def same(a, b, eps=1e-4):
    return abs(a[0] - b[0]) < eps and abs(a[1] - b[1]) < eps


def find_segment(board, net, a, b, layer):
    for track in list(board.GetTracks()):
        if track.Type() == p.PCB_VIA_T:
            continue
        if track.GetLayer() != layer or track.GetNetname().lstrip("/") != net:
            continue
        start = (track.GetStart().x / 1e6, track.GetStart().y / 1e6)
        end = (track.GetEnd().x / 1e6, track.GetEnd().y / 1e6)
        if (same(start, a) and same(end, b)) or (same(start, b) and same(end, a)):
            return track
    return None


def add_segment(board, net, a, b, layer):
    if math.dist(a, b) < 1e-6:
        return
    item = p.PCB_TRACK(board)
    item.SetStart(vec(a))
    item.SetEnd(vec(b))
    item.SetLayer(layer)
    item.SetWidth(mm(0.15))
    item.SetNet(board.FindNet(net))
    item.SetLocked(True)
    board.Add(item)


def main():
    board = p.LoadBoard(str(PCB))
    old = find_segment(board, "USB_DM", (50.8941, 26.155), (53.0675, 26.155), p.F_Cu)
    if old is None:
        # Make the script safely repeatable after the jog has been applied.
        jog = find_segment(board, "USB_DM", (50.8941, 26.155), (50.8941, 26.18), p.F_Cu)
        if jog is not None:
            print("USB_DM clearance jog already present")
            return
        raise RuntimeError("original USB_DM segment not found")

    # Reuse the original object for the first leg.  This avoids deleting an
    # object and then touching KiCad's invalidated SWIG track collection.
    # The y=26.18 leg passes just below the USB_DP via.  A shallow diagonal
    # then rises to y=26.13 on the right side of the via pair, where the
    # PA10 via and the USB_DP pad both have >0.15 mm copper clearance.
    old.SetEnd(vec((50.8941, 26.18)))
    add_segment(board, "USB_DM", (50.8941, 26.18), (51.84, 26.18), p.F_Cu)
    add_segment(board, "USB_DM", (51.84, 26.18), (52.00, 26.13), p.F_Cu)
    add_segment(board, "USB_DM", (52.00, 26.13), (53.0675, 26.155), p.F_Cu)
    filler = p.ZONE_FILLER(board)
    filler.Fill(list(board.Zones()))
    p.SaveBoard(str(PCB), board)
    print("USB_DM clearance jog applied")


if __name__ == "__main__":
    main()
