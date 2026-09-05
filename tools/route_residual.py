"""Route the small residual set left by the constrained autorouter.

Freerouting is intentionally run before this script.  It is good at the bulk
of the board but may leave a few nets unrouted when the two external signal
layers are crowded.  This pass uses a conservative raster search for a short
F.Cu escape from each SMD pad, changes layer through a through via, and then
uses an inner-layer corridor to the through-hole header pad.  The inner-layer
tracks are accepted only after KiCad DRC and plane refill; the script never
deletes another net's copper.
"""
from __future__ import annotations

import argparse
import math
import pathlib
import sys

import pcbnew as p

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from local_router import route, exact_clear, exact_via_clear
from project_config import PCB, VIA_DIAMETER, VIA_DRILL


RESIDUAL = [
    ("PB11", "U1", "70", "J1", "16"),
    ("PB10", "U1", "69", "J1", "15"),
    ("PB12", "U1", "73", "J1", "17"),
    ("PB15", "U1", "76", "J1", "20"),
    ("PB2", "U1", "48", "J1", "21"),
    ("PD2", "U1", "116", "J1", "50"),
    ("PD3", "U1", "117", "J1", "51"),
    ("PE12", "U1", "65", "J2", "9"),
    ("PE5", "U1", "4", "J2", "16"),
    ("PE7", "U1", "58", "J2", "18"),
    ("PF14", "U1", "54", "J2", "27"),
    ("PF3", "U1", "13", "J2", "30"),
    ("PF4", "U1", "14", "J2", "31"),
    ("PF5", "U1", "15", "J2", "32"),
    ("PG0", "U1", "56", "J2", "37"),
]


def mm(v: float) -> int:
    return p.FromMM(v)


def vec(xy: tuple[float, float]) -> p.VECTOR2I:
    return p.VECTOR2I(mm(xy[0]), mm(xy[1]))


def xy(item) -> tuple[float, float]:
    q = item.GetPosition()
    return q.x / 1e6, q.y / 1e6


def get_pad(board, ref: str, number: str):
    fp = next(f for f in board.GetFootprints() if f.GetReference() == ref)
    # Conn/SW footprints can have duplicate pad numbers.  For this residual
    # set the source is unique and all destination header pads are unique.
    return next(q for q in fp.Pads() if q.GetNumber() == number)


def add_track(board, net, a, b, layer):
    if math.dist(a, b) < 1e-5:
        return
    t = p.PCB_TRACK(board)
    t.SetStart(vec(a))
    t.SetEnd(vec(b))
    t.SetLayer(layer)
    t.SetWidth(mm(0.20))
    t.SetNet(net)
    t.SetLocked(True)
    board.Add(t)


def add_via(board, net, point):
    v = p.PCB_VIA(board)
    v.SetPosition(vec(point))
    v.SetViaType(p.VIATYPE_THROUGH)
    v.SetWidth(mm(VIA_DIAMETER))
    v.SetDrill(mm(VIA_DRILL))
    v.SetLayerPair(p.F_Cu, p.B_Cu)
    v.SetNet(net)
    v.SetLocked(True)
    board.Add(v)


def radial_points(start):
    # Keep a short escape first.  Larger radii are used only where the QFP
    # fanout is already occupied by an existing track.
    for radius in (0.8, 1.2, 1.6, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0):
        for angle in range(0, 360, 15):
            a = math.radians(angle)
            yield start[0] + radius * math.cos(a), start[1] + radius * math.sin(a)


def find_path(board, source, target, netcode):
    """Return (F.Cu path, via point, inner path, inner layer)."""
    start, end = xy(source), xy(target)
    for via_point in radial_points(start):
        if not (0.7 < via_point[0] < 84.3 and 0.7 < via_point[1] < 64.3):
            continue
        # A* on F.Cu provides a real escape rather than assuming a straight
        # fanout.  This matters for the 0.5 mm-pitch MCU pads.
        front = route(board, netcode, start, via_point, 0.20, p.F_Cu, 10.0, 0.10)
        if front is None or not exact_clear(board, front, netcode, p.F_Cu):
            continue
        if not exact_via_clear(board, via_point, netcode, VIA_DIAMETER):
            continue
        # Prefer B.Cu because it is the signal layer on this four-layer
        # board; inner layers remain a fallback when the back is occupied.
        for layer in (p.B_Cu, p.In1_Cu, p.In2_Cu):
            inner = route(board, netcode, via_point, end, 0.20, layer, 10.0, 0.20)
            if inner is not None and exact_clear(board, inner, netcode, layer):
                return front, via_point, inner, layer
    return None


def main(only=()):
    board = p.LoadBoard(str(PCB))
    chosen = [x for x in RESIDUAL if not only or x[0] in only]
    for name, src_ref, src_num, dst_ref, dst_num in chosen:
        src = get_pad(board, src_ref, src_num)
        dst = get_pad(board, dst_ref, dst_num)
        result = find_path(board, src, dst, src.GetNetCode())
        if result is None:
            raise RuntimeError(f"no conservative residual route for {name}")
        front, via_point, inner, layer = result
        net = src.GetNet()
        for a, b in zip(front, front[1:]):
            add_track(board, net, a, b, p.F_Cu)
        add_via(board, net, via_point)
        for a, b in zip(inner, inner[1:]):
            add_track(board, net, a, b, layer)
        print(f"{name}: F.Cu escape + via {via_point} + {layer if isinstance(layer, str) else board.GetLayerName(layer)} ({len(inner)-1} segments)", flush=True)

    # Refill after adding through vias/tracks so plane voids are represented in
    # the saved board before the independent CLI DRC is run.
    filler = p.ZONE_FILLER(board)
    filler.Fill(list(board.Zones()))
    p.SaveBoard(str(PCB), board)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--nets", nargs="*", default=())
    args = parser.parse_args()
    main(tuple(args.nets))
