"""Merge the legacy VCAP1/VCAP2 copper nets into the schematic's VCAP net.

The routed snapshot predates the schematic cleanup and used one net per MCU
VCAP pin.  The STM32 data sheet specifies both pins as one analog supply node,
so the board must carry a single ``VCAP`` net that includes U1.71, U1.106,
both 2.2 uF capacitors and TP3.
"""
from __future__ import annotations

import pathlib
import sys

import pcbnew as p

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from project_config import PCB


def main():
    board = p.LoadBoard(str(PCB))
    vcap = board.FindNet("VCAP")
    if vcap is None:
        vcap = p.NETINFO_ITEM(board, "VCAP")
        board.Add(vcap)

    changed = 0
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname().lstrip("/") in {"VCAP1", "VCAP2"}:
                pad.SetNet(vcap)
                changed += 1

    for item in list(board.GetTracks()):
        if item.GetNetname().lstrip("/") in {"VCAP1", "VCAP2"}:
            item.SetNet(vcap)
            changed += 1

    # Keep displayed values aligned with the source schematic after the net
    # merge.  These fields are fabrication metadata, not electrical nets.
    for ref, value in (("C40", "2.2uF"), ("C41", "2.2uF"), ("TP3", "VCAP")):
        for fp in board.GetFootprints():
            if fp.GetReference() == ref:
                fp.SetValue(value)

    filler = p.ZONE_FILLER(board)
    filler.Fill(list(board.Zones()))
    p.SaveBoard(str(PCB), board)
    print(f"VCAP net merge applied; reassigned {changed} pads/tracks")


if __name__ == "__main__":
    main()
