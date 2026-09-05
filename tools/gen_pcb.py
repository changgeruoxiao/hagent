#!/usr/bin/env python3
"""PCB 生成器(须用 KiCad 自带 python 运行): 网表 -> 4层板 + 预布局 + DSN 导出。

用法: <KiCad>/bin/python.exe tools/gen_pcb.py
依据: 规格书 §8 叠层/布线规则, §8.3 预布局策略。
坐标: KiCad 内部坐标(原点左上, y 向下), 板 75x55mm。
"""
import json
import math
import sys
from pathlib import Path

import pcbnew

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
from sch_build import parse  # noqa: E402

NET_FILE = WS / "kicad" / "stm32h743_core.net"
PCB_FILE = WS / "kicad" / "stm32h743_core.kicad_pcb"
DSN_FILE = WS / "kicad" / "stm32h743_core.dsn"
FP_DIR = Path(r"C:\Users\27417\AppData\Local\Programs\KiCad\10.0\share\kicad\footprints")

BOARD_W, BOARD_H = 85.0, 65.0
MCU_CENTER = (42.5, 32.5)

# ---- 固定布局(与原理图分区一致): (x, y, 旋转角) ----
PLACE = {
    "J1": (42.5, 3.2, 90),       "J2": (42.5, 61.8, 90),      # 2x28 排针, 上下长边(留边0.9+)
    "J3": (7.5, 24.0, 0),        # USB-C 左缘
    "J4": (3.2, 12.5, 0),       # SWD 左缘上
    "J5": (10.0, 55.0, 0),       # BOOT 跳线
    "J6": (3.2, 48.0, 0),       # 5VIN 左缘下
    # DCDC 区(左上角, 回路最小化)
    "U2": (18, 15, 0),  "L1": (27, 12, 0),  "D7": (25.5, 17.5, 270),
    "C23": (18, 10.8, 0),
    "C20": (10, 19, 270), "C21": (15, 20.8, 270), "C22": (17, 20.8, 270),
    "R14": (38.5, 12, 0),
    "C24": (35.5, 10.2, 270), "C25": (35.5, 15.2, 0),
    "R15": (22, 19.5, 270), "R16": (22, 22.5, 270),
    "R17": (15.5, 24.5, 0), "C26": (15, 29, 0), "C27": (24, 22, 0),
    # USB ESD(VBUS 分压 R12/R13 为 DNP)
    "U3": (19.5, 25, 90),
    "R10": (19, 30.5, 270), "R11": (22.5, 30.5, 270),
    "R12": (15, 31, 270), "R13": (15, 34.5, 270),
    # 时钟(MCU 下方)
    "X1": (35, 46, 0),  "C50": (33.5, 49.5, 270), "C51": (37, 49.5, 270),
    "X2": (47, 46, 0),  "C52": (45.5, 49.5, 270), "C53": (49, 49.5, 270),
    # 模拟电源链( MCU 左侧一列)
    "FB1": (27.5, 36, 0), "R20": (27.5, 40, 0),
    "C42": (25.5, 33.5, 270), "C43": (25.5, 37.5, 270),
    "C44": (23, 33.5, 270), "C45": (23, 37.5, 270),
    "R21": (31, 15.5, 270),       # VBAT 上拉
    "C48": (28, 15.5, 270),       # VBAT 100nF 去耦
    "R22": (28.5, 28.5, 270),     # PDR_ON 上拉
    # 指示与人机(右侧)
    "R24": (66, 38, 270), "D8": (66, 42.5, 270),
    "R25": (70, 38, 270), "D9": (70, 42.5, 270),
    "SW2": (72, 19, 0), "C55": (72, 24, 0),
    # 测试点(右缘一列)
    "TP1": (78.5, 40, 0), "TP2": (78.5, 43, 0), "TP3": (78.5, 46, 0),
    "TP4": (78.5, 49, 0), "TP5": (78.5, 52, 0), "TP6": (78.5, 55, 0),
    # 输入保护链 / 复位 / BOOT0 / 补位去耦
    "F1": (28.5, 22.5, 0),          # 保险丝(VBUS 后)
    "D5": (31.5, 18.5, 0),        # SS34 → +5V
    "D6": (9, 44, 270),           # 5VIN 合路
    "R23": (14, 55, 0),           # BOOT0 下拉(近 J5)
    "SW1": (25, 45, 0),           # NRST 按键(下方空区, 避开反馈电阻)
    "C54": (20.5, 33.5, 270),     # NRST 电容
    "C47": (40, 17, 270),         # VDD33_USB 100n(顶部固定)
    "C71": (24, 25, 0),         # 4.7uF 补位
    "C72": (62, 44, 0),           # 4.7uF 补位
}
MOUNT_HOLES = [(3.5, 33), (79, 33), (30, 55), (55, 55)]
HOLE_FP = "MountingHole:MountingHole_3.2mm_M3_Pad"   # plated+GND: 布线器可识别, 兼作屏蔽地

# 动态就近布局: MCU 引脚 -> (位号, 距 pad 中心 mm)
PIN_NEAR = {p: f"C{60 + i}" for i, p in enumerate(
    ["17", "30", "39", "52", "62", "72", "84", "108", "121", "131", "144"])}  # 11x100n
PIN_NEAR["71"] = "C40"    # VCAP1
PIN_NEAR["106"] = "C41"   # VCAP2
PIN_NEAR["95"] = "C46"    # VDD33_USB 1uF
CAP_DIST = {"C40": 4.0, "C41": 4.0, "C46": 4.5}


def parse_netlist():
    data = parse(NET_FILE.read_text(encoding="utf-8"))
    comps, nets = {}, {}
    for blk in data:
        if not (isinstance(blk, list) and blk):
            continue
        if blk[0] == "components":
            for c in blk[1:]:
                if not (isinstance(c, list) and c and c[0] == "comp"):
                    continue
                ref = next(x[1] for x in c if isinstance(x, list) and x[0] == "ref")
                val = next((x[1] for x in c if isinstance(x, list) and x[0] == "value"), "")
                fp = next((x[1] for x in c if isinstance(x, list) and x[0] == "footprint"), "")
                comps[ref] = (val, fp)
        elif blk[0] == "nets":
            for n in blk[1:]:
                if not (isinstance(n, list) and n and n[0] == "net"):
                    continue
                name = next(x[1] for x in n if isinstance(x, list) and x[0] == "name").lstrip("/")
                if name.startswith("unconnected-"):
                    continue
                nodes = []
                for y in n:
                    if isinstance(y, list) and y[0] == "node":
                        r = next(z[1] for z in y if isinstance(z, list) and z[0] == "ref")
                        p = next(z[1] for z in y if isinstance(z, list) and z[0] == "pin")
                        nodes.append((r, p))
                nets[name] = nodes
    return comps, nets


def mm(v: float) -> int:
    return pcbnew.FromMM(v)


def pad_bbox(fp, margin_mm=0.15):
    """焊盘包围盒 (x1, y1, x2, y2), 计入焊盘尺寸与 margin, 单位 mm。"""
    pts = []
    for p in fp.Pads():
        r = max(p.GetSize().x, p.GetSize().y) / 2
        pts.append((p.GetPosition().x - r, p.GetPosition().y - r))
        pts.append((p.GetPosition().x + r, p.GetPosition().y + r))
    m = mm(margin_mm)
    return ((min(x for x, _ in pts) - m) / 1e6, (min(y for _, y in pts) - m) / 1e6,
            (max(x for x, _ in pts) + m) / 1e6, (max(y for _, y in pts) + m) / 1e6)


def bbox_hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def place_footprint(board, ref, value, fp_id, x, y, angle, placed_bboxes=None):
    lib, name = fp_id.split(":")
    fp = pcbnew.FootprintLoad(str(FP_DIR / f"{lib}.pretty"), name)
    if fp is None:
        raise RuntimeError(f"封装不存在: {fp_id}")
    fp.SetReference(ref)
    try:
        fp.SetValue(value)
    except Exception:
        pass
    fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    fp.SetOrientationDegrees(angle)
    # 封装原点不统一(有的在1脚不在中心): 按焊盘包围盒把中心对齐到目标位置
    pads = list(fp.Pads())
    if pads:
        xs = [p.GetPosition().x for p in pads]
        ys = [p.GetPosition().y for p in pads]
        bcx, bcy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        cur = fp.GetPosition()
        fp.SetPosition(pcbnew.VECTOR2I(int(cur.x + mm(x) - bcx), int(cur.y + mm(y) - bcy)))
    # 焊盘包围盒矩形碰撞检查(权威门禁)
    if placed_bboxes is not None:
        bb = pad_bbox(fp)
        for oref, obb in placed_bboxes:
            if bbox_hit(bb, obb):
                raise RuntimeError(
                    f"焊盘包围盒重叠: {ref}{(x, y)} <-> {oref} (bbox {bb} vs {obb})")
        placed_bboxes.append((ref, bb))
    board.Add(fp)
    return fp


def rot_for_pad1_toward(fp_lib, fp_name, target_dir):
    """求旋转角使封装 pad1 朝向 target_dir(y-down 单位向量)。公式按 KiCad 内部旋转。"""
    tmp = pcbnew.FootprintLoad(str(FP_DIR / f"{fp_lib}.pretty"), fp_name)
    p1 = tmp.FindPadByNumber("1").GetPosition()  # 相对模块原点? 新加载的封装 pad 为绝对坐标(原点0)
    px, py = p1.x / 1e6, p1.y / 1e6  # nm->mm
    if abs(px) < 1e-3 and abs(py) < 1e-3:
        return 0.0
    # KiCad 旋转: x' = x cosT + y sinT ; y' = -x sinT + y cosT
    theta = math.atan2(px * target_dir[1] - py * target_dir[0],
                       px * target_dir[0] + py * target_dir[1])
    return math.degrees(theta)


def build():
    comps, nets = parse_netlist()
    assert "U1" in comps and "J1" in comps, "网表不完整"
    print(f"网表: {len(comps)} 元件, {len(nets)} 网络")

    board = pcbnew.BOARD()
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(4)
    nc = ds.m_NetSettings.GetDefaultNetclass()
    nc.SetClearance(mm(0.15))
    nc.SetTrackWidth(mm(0.2))
    nc.SetViaDiameter(mm(0.5))
    nc.SetViaDrill(mm(0.25))
    ds.m_CopperEdgeClearance = mm(0.3)
    ds.m_HoleToHoleMin = mm(0.5)
    ds.m_MinThroughDrill = mm(0.25)
    nc.SetTrackWidth(mm(0.15))   # DRC 下限=规格书最小线宽; 默认布线宽度由 DSN 类规则(0.2)控制

    # 网络
    net_items = {}
    for name in nets:
        item = pcbnew.NETINFO_ITEM(board, name)
        board.Add(item)
        net_items[name] = item
    gnd = net_items["GND"]

    # 板框
    edge = pcbnew.PCB_SHAPE(board)
    edge.SetShape(pcbnew.SHAPE_T_RECT)
    edge.SetStart(pcbnew.VECTOR2I(0, 0))
    edge.SetEnd(pcbnew.VECTOR2I(mm(BOARD_W), mm(BOARD_H)))
    edge.SetLayer(pcbnew.Edge_Cuts)
    board.Add(edge)

    # 静态包络断言已由放置时的焊盘包围盒矩形检查取代(更精确)

    # 固定布局
    fps = {}
    placed_bboxes = []
    for ref, (x, y, ang) in PLACE.items():
        val, fp_id = comps[ref]
        fps[ref] = place_footprint(board, ref, val, fp_id, x, y, ang, placed_bboxes)
    # MCU
    val, fp_id = comps["U1"]
    u1 = place_footprint(board, "U1", val, fp_id, *MCU_CENTER, 0, placed_bboxes)
    fps["U1"] = u1
    # 安装孔(接地)
    for i, (x, y) in enumerate(MOUNT_HOLES, 1):
        hfp = place_footprint(board, f"H{i}", "M3", HOLE_FP, x, y, 0, placed_bboxes)
        hpad = hfp.FindPadByNumber("1")
        if hpad is not None:
            hpad.SetNet(gnd)

    # 动态就近布局(去耦/VCAP/VDD33USB): 径向外推 + 碰撞规避
    ENVELOPE = {"J": 4.5, "U": 3.0, "SW": 4.0, "X": 3.0, "L": 4.0, "F": 2.0,
                "D": 1.5, "FB": 1.5, "TP": 1.5, "C": 1.3, "R": 1.3}

    def env_of(ref: str) -> float:
        return ENVELOPE.get(ref[:2], ENVELOPE.get(ref[0], 1.5))

    cx, cy = mm(MCU_CENTER[0]), mm(MCU_CENTER[1])
    placed_env = [(x, y, env_of(ref)) for ref, (x, y, _a) in PLACE.items()]
    for pin, cap_ref in PIN_NEAR.items():
        val, fp_id = comps[cap_ref]
        lib, name = fp_id.split(":")
        pad = u1.FindPadByNumber(pin)
        px, py = pad.GetPosition().x, pad.GetPosition().y
        dx, dy = px - cx, py - cy
        norm = math.hypot(dx, dy)
        ux, uy = dx / norm, dy / norm
        dist = CAP_DIST.get(cap_ref, 4.5)
        # 碰撞规避: 径向外推为主, 死角(板角/密集区)则换向重试
        best = None
        for ang_off in (0, 35, -35, 70, -70, 110, -110):
            a = math.radians(ang_off)
            ux2 = ux * math.cos(a) - uy * math.sin(a)
            uy2 = ux * math.sin(a) + uy * math.cos(a)
            dist = CAP_DIST.get(cap_ref, 4.5)
            for _try in range(7):
                cap_x, cap_y = px + ux2 * mm(dist), py + uy2 * mm(dist)
                cxm, cym = cap_x / 1e6, cap_y / 1e6
                hit = any(math.hypot(cxm - ex, cym - ey) < er + 1.6 for ex, ey, er in placed_env)
                inside = 2.0 < cxm < BOARD_W - 2.0 and 2.0 < cym < BOARD_H - 2.0
                if (not hit and inside) or dist > 16:
                    break
                dist += 1.6
            if not hit and inside:
                best = (cap_x, cap_y, ux2, uy2)
                break
            best = best or (cap_x, cap_y, ux2, uy2)
        cap_x, cap_y, ux2, uy2 = best
        ang = rot_for_pad1_toward(lib, name, (-ux2, -uy2))
        fps[cap_ref] = place_footprint(board, cap_ref, val, fp_id,
                                       cap_x / 1e6, cap_y / 1e6, ang, placed_bboxes)
        placed_env.append((cap_x / 1e6, cap_y / 1e6, 1.3))

    # 焊盘网络分配(同名多 pad 全部赋网, 如轻触开关的双腿"1"/"2")
    missing = []
    for net_name, nodes in nets.items():
        for ref, pin in nodes:
            fp = fps.get(ref)
            if fp is None:
                missing.append(f"{ref}.{pin}(无封装)")
                continue
            matched = [p for p in fp.Pads() if p.GetName() == pin]
            if not matched:
                missing.append(f"{ref}.{pin}(封装无此pad)")
                continue
            for pad in matched:
                pad.SetNet(net_items[net_name])
    # USB-C 屏蔽脚: 符号叫 SH, 封装为 S1/S2
    j3 = fps["J3"]
    for s in ("S1", "S2"):
        p = j3.FindPadByNumber(s)
        if p is not None:
            p.SetNet(gnd)
    if missing:
        print("!! pad 匹配失败:")
        for m0 in missing[:20]:
            print("   ", m0)
        raise SystemExit(1)

    # ---- 预布线(种子): 3 条长距离难布网先手工定线, Freerouting 绕开它们布其余 ----
    pre_objs = []

    def add_via(pos_mm, n):
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(mm(pos_mm[0]), mm(pos_mm[1])))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetWidth(mm(0.4))
        v.SetDrill(mm(0.2))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(n)
        board.Add(v)
        pre_objs.append(v)
        return v

    def add_track(p1, p2, layer, n):
        tr = pcbnew.PCB_TRACK(board)
        tr.SetStart(pcbnew.VECTOR2I(mm(p1[0]), mm(p1[1])))
        tr.SetEnd(pcbnew.VECTOR2I(mm(p2[0]), mm(p2[1])))
        tr.SetWidth(mm(0.2))
        tr.SetLayer(layer)
        tr.SetNet(n)
        board.Add(tr)
        pre_objs.append(tr)

    U1F = fps["U1"]
    in2 = pcbnew.In2_Cu
    # PF4: pad14 犬骨左出 → In2 左缘下行 → J2.31 (THT 直连)
    pf4_pad = U1F.FindPadByNumber("14")
    pf4_net = pf4_pad.GetNet()
    pf4_via = add_via((31.84, 30.25), pf4_net)  # 过孔入盘(tented)
    pf4_path = [(31.84, 30.25), (31.84, 6), (6.5, 6), (6.5, 61.8), (47, 61.8), (47, 63.07), (46.31, 63.07)]
    prev = pf4_via.GetPosition()
    for wx, wy in pf4_path[1:]:
        pt = pcbnew.VECTOR2I(mm(wx), mm(wy))
        add_track((prev.x / 1e6, prev.y / 1e6), (wx, wy), pcbnew.B_Cu, pf4_net)
        prev = pt
    # PB10: J1.15 THT 直连 → In2 上缘右行 → 下行 → 过孔 → pad69
    pb10_net = net_items["PB10"]
    pb10_path = [(49.75, 43.16), (25.99, 4.47)]
    prev = None
    for wx, wy in pb10_path:
        pt = pcbnew.VECTOR2I(mm(wx), mm(wy))
        if prev is not None:
            add_track((prev.x / 1e6, prev.y / 1e6), (wx, wy), pcbnew.B_Cu, pb10_net)
        prev = pt
    add_via((49.75, 43.16), pb10_net)
    # PB11: J1.16 THT 直连 → In2 板缘走廊 → 右缘下行 → 过孔 → pad70
    pb11_net = net_items["PB11"]
    pb11_path = [(50.25, 43.16), (50.25, 47), (84, 47), (84, 0.6), (25.99, 0.6), (25.99, 1.93)]
    prev = None
    for wx, wy in pb11_path:
        pt = pcbnew.VECTOR2I(mm(wx), mm(wy))
        if prev is not None:
            add_track((prev.x / 1e6, prev.y / 1e6), (wx, wy), pcbnew.B_Cu, pb11_net)
        prev = pt
    add_via((50.25, 43.16), pb11_net)
    out_n = len(pre_objs)
    ok = pcbnew.ExportSpecctraDSN(board, str(DSN_FILE))
    print(f"预布线 3 条({out_n} 对象) + DSN 导出 {'OK' if ok else '失败'}")
    # 移除预布线对象, 最终板交由 SES 导入恢复全部走线(避免重复)
    for o in pre_objs:
        board.Remove(o)
    pcbnew.SaveBoard(str(PCB_FILE), board)
    print("已保存(无走线状态)")
    # 最小工程文件会把网络类静默重置为 KiCad 默认(间距0.2), 必须显式声明!
    pro = PCB_FILE.with_suffix(".kicad_pro")

    def netclass(name, width):
        return {"name": name, "clearance": 0.15, "track_width": width,
                "via_diameter": 0.5, "via_drill": 0.25, "uvia_diameter": 0.3,
                "uvia_drill": 0.1, "diff_pair_width": 0.2, "diff_pair_gap": 0.25,
                "diff_pair_via_gap": 0.25, "bus_width": 0.25,
                "wire_width": 0.2, "pcb_color": "rgba(0, 0, 0, 0.000)"}

    pro.write_text(json.dumps({
        "board": {"design_settings": {
            "rules": {
                "min_clearance": 0.15, "min_track_width": 0.15,
                "min_through_hole_diameter": 0.2, "min_via_diameter": 0.4,
                "min_via_annular_width": 0.1, "min_hole_clearance": 0.25,
                "min_hole_to_hole": 0.25, "min_copper_edge_clearance": 0.3,
                "min_silk_clearance": 0.0, "min_text_height": 0.8,
                "min_text_thickness": 0.08},
            "rule_severities": {
            "courtyards_overlap": "warning", "silk_over_copper": "warning",
            "silk_overlap": "warning", "silk_edge_clearance": "warning",
            "solder_mask_bridge": "warning", "pth_inside_courtyard": "warning",
            "npth_inside_courtyard": "warning", "hole_to_hole": "warning",
            "via_dangling": "warning"}}},
        "net_settings": {"classes": [netclass("Default", 0.15), netclass("Power", 0.3)]},
        "meta": {"filename": pro.name, "version": 3}}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"已保存 {PCB_FILE.name} (无走线状态, DSN 已含预布线)")

    # 自检: 每个网络的已分配 pad 数 = 网表节点数
    for net_name, nodes in nets.items():
        got = sum(1 for fp in board.GetFootprints() for p in fp.Pads()
                  if p.GetNetname() == net_name)
        if got < len(nodes):
            print(f"!! 网络 {net_name}: 网表 {len(nodes)} 节点, 板上仅 {got} pad")
            raise SystemExit(1)
    print(f"pad 网络分配校验通过({len(nets)} 网络)")


if __name__ == "__main__":
    build()
