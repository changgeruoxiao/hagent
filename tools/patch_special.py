"""Close the two non-header residuals after bulk residual routing.

VCAP1 and VCAP2 are one logical VCAP net, but they are separate SMD pads, so
the two existing capacitor branches need one explicit copper link.  PC13 is
the second duplicate contact of the four-pad user switch; the first contact is
already routed by Freerouting and the two switch contacts are joined on B.Cu.
"""
from __future__ import annotations

import math
import pathlib
import sys

import pcbnew as p

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from local_router import route, exact_clear, exact_via_clear
from project_config import PCB, VIA_DIAMETER, VIA_DRILL


def mm(v):
    return p.FromMM(v)


def vec(xy):
    return p.VECTOR2I(mm(xy[0]), mm(xy[1]))


def xy(q):
    return q.GetPosition().x / 1e6, q.GetPosition().y / 1e6


def pad(board, ref, number, x=None):
    fp = next(f for f in board.GetFootprints() if f.GetReference() == ref)
    pads = [q for q in fp.Pads() if q.GetNumber() == number]
    if x is not None:
        return min(pads, key=lambda q: abs(q.GetPosition().x / 1e6 - x))
    return pads[0]


def add_track(board, net, a, b, layer, width=0.2):
    if math.dist(a, b) < 1e-5:
        return
    t = p.PCB_TRACK(board)
    t.SetStart(vec(a)); t.SetEnd(vec(b)); t.SetLayer(layer)
    t.SetWidth(mm(width)); t.SetNet(net); t.SetLocked(True); board.Add(t)


def add_via(board, net, point):
    v = p.PCB_VIA(board)
    v.SetPosition(vec(point)); v.SetViaType(p.VIATYPE_THROUGH)
    v.SetWidth(mm(VIA_DIAMETER)); v.SetDrill(mm(VIA_DRILL))
    v.SetLayerPair(p.F_Cu, p.B_Cu); v.SetNet(net); v.SetLocked(True)
    board.Add(v)


def radial(pos):
    for radius in (0.8, 1.2, 1.6, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0):
        for angle in range(0, 360, 15):
            a = math.radians(angle)
            yield pos[0] + radius * math.cos(a), pos[1] + radius * math.sin(a)


def connect_vcap(board):
    a = pad(board, "U1", "71")
    b = pad(board, "U1", "106")
    net = a.GetNet(); ap, bp = xy(a), xy(b)
    # Use two local vias and an inner corridor.  This keeps the link away from
    # the QFP body while preserving the existing short capacitor fanouts.
    for va in radial(ap):
        front_a = route(board, net.GetNetCode(), ap, va, 0.2, p.F_Cu, 10.0, 0.1)
        if front_a is None or not exact_clear(board, front_a, net.GetNetCode(), p.F_Cu):
            continue
        if not exact_via_clear(board, va, net.GetNetCode(), VIA_DIAMETER):
            continue
        for vb in radial(bp):
            front_b = route(board, net.GetNetCode(), bp, vb, 0.2, p.F_Cu, 10.0, 0.1)
            if front_b is None or not exact_clear(board, front_b, net.GetNetCode(), p.F_Cu):
                continue
            if not exact_via_clear(board, vb, net.GetNetCode(), VIA_DIAMETER):
                continue
            for layer in (p.In1_Cu, p.In2_Cu):
                inner = route(board, net.GetNetCode(), va, vb, 0.2, layer, 10.0, 0.2)
                if inner is None or not exact_clear(board, inner, net.GetNetCode(), layer):
                    continue
                for x, y in zip(front_a, front_a[1:]):
                    add_track(board, net, x, y, p.F_Cu)
                for x, y in zip(front_b, front_b[1:]):
                    add_track(board, net, x, y, p.F_Cu)
                add_via(board, net, va); add_via(board, net, vb)
                for x, y in zip(inner, inner[1:]):
                    add_track(board, net, x, y, layer)
                print(f"VCAP: linked U1.71/U1.106 via {va} -> {vb} on {board.GetLayerName(layer)}", flush=True)
                return
    raise RuntimeError("no VCAP bridge found")


def connect_switch(board):
    sw = next(f for f in board.GetFootprints() if f.GetReference() == "SW2")
    contacts = [q for q in sw.Pads() if q.GetNumber() == "1"]
    # The left contact at x=67.75 is on the routed PC13 branch.  Join the
    # right contact directly on B.Cu; both are through-hole pads.
    left = min(contacts, key=lambda q: q.GetPosition().x)
    right = max(contacts, key=lambda q: q.GetPosition().x)
    net = left.GetNet(); a, b = xy(right), xy(left)
    path = route(board, net.GetNetCode(), a, b, 0.2, p.B_Cu, 6.0, 0.1)
    if path is None or not exact_clear(board, path, net.GetNetCode(), p.B_Cu):
        raise RuntimeError("no PC13 switch-contact bridge found")
    for x, y in zip(path, path[1:]):
        add_track(board, net, x, y, p.B_Cu)
    print(f"PC13: joined SW2 contacts on B.Cu ({len(path)-1} segments)", flush=True)


def main():
    board = p.LoadBoard(str(PCB))
    connect_vcap(board)
    connect_switch(board)
    filler = p.ZONE_FILLER(board)
    filler.Fill(list(board.Zones()))
    p.SaveBoard(str(PCB), board)


if __name__ == "__main__":
    main()
