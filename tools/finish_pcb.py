#!/usr/bin/env python3
"""布线回写与收尾(须用 KiCad 自带 python 运行): SES 导入 + GND/电源整区灌铜 + 保存。"""
import sys
from pathlib import Path

import pcbnew

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
from project_config import BOARD_W, BOARD_H  # noqa: E402

PCB = WS / "kicad" / "stm32h743_core.kicad_pcb"
SES = WS / "kicad" / "stm32h743_core.ses"


def main():
    board = pcbnew.LoadBoard(str(PCB))
    if not pcbnew.ImportSpecctraSES(board, str(SES)):
        print("!! SES 导入失败")
        raise SystemExit(1)
    tracks = len(list(board.GetTracks()))
    print(f"SES 导入 OK: {tracks} 个走线/过孔对象")

    # 细线归一: 布线器偶发低于最小线宽的段统一抬到 0.15mm(规格书下限)
    fixed = 0
    for t in board.GetTracks():
        if t.Type() != pcbnew.PCB_VIA_T and t.GetWidth() < pcbnew.FromMM(0.15):
            t.SetWidth(pcbnew.FromMM(0.15))
            fixed += 1
    if fixed:
        print(f"细线归一: {fixed} 段 <0.15mm 已抬宽")

    net_by_name = {}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            nm = pad.GetNetname()
            if nm and nm not in net_by_name:
                net_by_name[nm] = pad.GetNet()

    def add_zone(layer, net_name):
        zone = pcbnew.ZONE(board)
        zone.SetLayer(layer)
        zone.SetNet(net_by_name[net_name])
        po = zone.Outline()
        po.NewOutline()
        # 板尺寸只能来自 project_config，禁止历史尺寸常量在收尾脚本中漂移。
        for x, y in ((0, 0), (BOARD_W, 0), (BOARD_W, BOARD_H), (0, BOARD_H)):
            po.Append(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        zone.SetMinThickness(pcbnew.FromMM(0.15))
        try:
            zone.SetLocalClearance(pcbnew.FromMM(0.3))
        except Exception:
            pass
        try:
            zone.SetThermalReliefGap(pcbnew.FromMM(0.25))
            zone.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.3))
        except Exception:
            pass
        board.Add(zone)
        return zone

    z1 = add_zone(pcbnew.In1_Cu, "GND")
    z2 = add_zone(pcbnew.In2_Cu, "+3V3")
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill([z1, z2])
    print(f"灌铜完成: {BOARD_W:g}x{BOARD_H:g}mm")

    pcbnew.SaveBoard(str(PCB), board)
    print("已保存", PCB.name)


if __name__ == "__main__":
    main()
