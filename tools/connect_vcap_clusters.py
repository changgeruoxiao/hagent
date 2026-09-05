"""Connect the two legacy VCAP copper islands after net-name merging."""
from __future__ import annotations

import math
import pathlib
import sys

import pcbnew as p

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from local_router import exact_clear, route
from project_config import PCB


def vec(xy):
    return p.VECTOR2I(p.FromMM(xy[0]), p.FromMM(xy[1]))


def has_segment(board, net_name, a, b, layer, eps=1e-4):
    """Return true when an exact endpoint pair is already present."""
    def pt(item):
        q = item.GetStart()
        return q.x / 1e6, q.y / 1e6
    for item in board.GetTracks():
        if item.Type() == p.PCB_VIA_T or item.GetLayer() != layer:
            continue
        if item.GetNetname().lstrip("/") != net_name:
            continue
        s = pt(item)
        q = item.GetEnd()
        e = q.x / 1e6, q.y / 1e6
        if ((math.dist(s, a) < eps and math.dist(e, b) < eps) or
                (math.dist(s, b) < eps and math.dist(e, a) < eps)):
            return True
    return False


def main():
    board = p.LoadBoard(str(PCB))
    net = board.FindNet("VCAP")
    if net is None:
        raise RuntimeError("VCAP net is missing; run merge_vcap_net.py first")

    # Existing through vias are the copper anchors for the two islands.  The
    # In2 route follows a clear corridor around the right board edge.
    start = (50.7516, 44.7457)  # U1.71/C40/TP3 island
    end = (54.5893, 24.8729)    # U1.106/C41 island
    # The first and last legs are stable outputs of the deterministic router;
    # use them as an idempotence marker when the workflow is re-run.
    if (has_segment(board, "VCAP", start, (50.8, 44.7), p.In2_Cu) and
            has_segment(board, "VCAP", (54.6, 24.9), end, p.In2_Cu)):
        print("VCAP corridor already present")
        return
    points = route(board, net.GetNetCode(), start, end, 0.15, p.In2_Cu,
                   margin=25.0, step=0.1)
    if points is None:
        raise RuntimeError("unable to find a clear In2.Cu VCAP corridor")
    if not exact_clear(board, points, net.GetNetCode(), p.In2_Cu, 0.15, 0.15):
        raise RuntimeError("router returned a path that fails exact clearance")

    added = 0
    for a, b in zip(points, points[1:]):
        if math.dist(a, b) < 1e-6:
            continue
        track = p.PCB_TRACK(board)
        track.SetStart(vec(a))
        track.SetEnd(vec(b))
        track.SetWidth(p.FromMM(0.15))
        track.SetLayer(p.In2_Cu)
        track.SetNet(net)
        track.SetLocked(True)
        board.Add(track)
        added += 1

    filler = p.ZONE_FILLER(board)
    filler.Fill(list(board.Zones()))
    p.SaveBoard(str(PCB), board)
    print(f"VCAP islands connected on In2.Cu with {added} segments")


if __name__ == "__main__":
    main()
