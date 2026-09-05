#!/usr/bin/env python3
"""网表正确性门禁: 以规格书附录A + 设计规则为独立真源, 断言导出网表的连通性。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sch_build import parse, LibCache

from project_config import NET as NET_FILE

# ---- 独立真源(手写自规格书, 不复用生成器代码) ----
VDD = {17, 30, 39, 52, 62, 72, 84, 108, 121, 131, 144}
VSS = {16, 38, 51, 61, 83, 94, 107, 120, 130}
VDD33USB = 95
MCU_POWER = {"+3V3": {str(n) for n in VDD | {VDD33USB}},
             "GND": {str(n) for n in VSS | {31}}}
MCU_SPECIAL = {
    "VDDA": "33", "VREF+": "32", "VBAT": "6", "PDR_ON": "143",
    "NRST": "25", "BOOT0": "138", "OSC_IN": "23", "OSC_OUT": "24",
    "OSC32_IN": "8", "OSC32_OUT": "9", "USB_DM": "103", "USB_DP": "104",
}

# 每个网络的期望节点集(None=仅检查包含子集; tuple=(必须包含, 必须不含))
EXPECT = {
    "+3V3": ({f"U1.{p}" for p in MCU_POWER["+3V3"]} | {"R14.2", "R25.1", "R21.1", "R22.2", "R24.1",
             "J4.1", "J5.1", "J1.54", "J2.53", "J2.54", "TP1.1", "C46.1", "C47.1",
             "FB1.1"}, None),
    "GND": ({f"U1.{p}" for p in MCU_POWER["GND"]} | {"U2.7", "U2.9", "U3.2", "R11.2", "R10.2",
             "R16.2", "R23.2", "C26.2", "C27.2", "D7.2", "D8.1", "C48.2", "SW1.2", "SW2.2",
             "J3.A1", "J3.A12", "J3.B1", "J3.B12", "J4.6", "J5.3", "J1.55", "J1.56", "J2.55", "J2.56", "TP2.1"}, None),
    "VDDA": ({"U1.33", "FB1.2", "C42.1", "C43.1", "R20.1"}, set()),
    "VREF+": ({"U1.32", "R20.2", "C44.1", "C45.1"}, set()),
    "VBAT": ({"U1.6", "R21.2", "C48.1"}, set()),
    "VCAP": ({"U1.71", "U1.106", "C40.1", "C41.1", "TP3.1"}, set()),
    "PDR_ON": ({"U1.143", "R22.1"}, set()),
    "NRST": ({"U1.25", "SW1.1", "C54.1", "J4.5", "TP4.1"}, set()),
    "BOOT0": ({"U1.138", "R23.1", "J5.2", "TP5.1"}, set()),
    "OSC_IN": ({"U1.23", "X1.1", "C50.1"}, set()),
    "OSC_OUT": ({"U1.24", "X1.2", "C51.1"}, set()),
    "OSC32_IN": ({"U1.8", "X2.1", "C52.1"}, set()),
    "OSC32_OUT": ({"U1.9", "X2.2", "C53.1"}, set()),
    "USB_DM": ({"U1.103", "U3.3"}, set()),
    "USB_DP": ({"U1.104", "U3.1"}, set()),
    "USB_DM_P": ({"U3.4"}, {"U1.*"}),
    "USB_DP_P": ({"U3.6"}, {"U1.*"}),
    "VBUS": ({"F1.1", "R12.1", "J3.A4", "J3.A9", "J3.B4", "J3.B9", "U3.5"}, {"U1.*", "U2.*"}),
    "VBUS_F": ({"F1.2", "D5.2"}, set()),
    "5VIN": ({"J6.1", "D6.2"}, set()),
    "+5V": ({"D5.1", "D6.1", "U2.2", "C20.1", "C21.1", "C22.1"}, set()),
    "PH": ({"U2.8", "D7.1", "L1.1", "C23.2"}, set()),
    "BOOT": ({"U2.1", "C23.1"}, set()),
    "FB": ({"U2.5", "R15.2", "R16.1"}, set()),
    "COMP": ({"U2.6", "R17.1", "C27.1"}, set()),
    "COMP_M": ({"R17.2", "C26.1"}, set()),
    "3V3_SW": ({"L1.2", "R14.1", "C24.1", "C25.1", "R15.1", "TP6.1"}, set()),
    "LED_USER": ({"R25.2", "D9.2"}, set()),
    "PB0": ({"U1.46", "D9.1"}, None),
    "CC1": ({"J3.A5", "R10.1"}, set()),
    "CC2": ({"J3.B5", "R11.1"}, set()),
}
# DNP 网络豁免
DNP_NETS = {"VBUS_SENSE"}
# 去耦: C60..C72 = 13 颗(11x100n + 2x4.7u) 在 +3V3/GND 上
DECAP_REFS = [f"C{n}" for n in range(60, 73)]


def main():
    data = parse(NET_FILE.read_text(encoding="utf-8"))
    nets = {}
    for blk in data:
        if isinstance(blk, list) and blk and blk[0] == "nets":
            for net_e in blk[1:]:
                if not (isinstance(net_e, list) and net_e and net_e[0] == "net"):
                    continue
                name = next(x[1] for x in net_e if isinstance(x, list) and x[0] == "name")
                if name.startswith("unconnected-"):
                    continue
                name = name.lstrip("/")
                nodes = set()
                for y in net_e:
                    if isinstance(y, list) and y[0] == "node":
                        r = next(z[1] for z in y if isinstance(z, list) and z[0] == "ref")
                        p = next(z[1] for z in y if isinstance(z, list) and z[0] == "pin")
                        nodes.add(f"{r}.{p}")
                nets[name] = nodes

    errors = []
    # 1. 期望网络逐个断言
    for net, (must, forbidden) in EXPECT.items():
        if net not in nets:
            errors.append(f"缺少网络 {net}")
            continue
        for pat in must:
            if pat.endswith("*"):
                if not any(n.startswith(pat[:-1]) for n in nets[net]):
                    errors.append(f"{net}: 无匹配 {pat} 的节点(实际 {sorted(nets[net])})")
            elif pat not in nets[net]:
                errors.append(f"{net}: 缺节点 {pat} (实际 {sorted(nets[net])})")
        if forbidden:
            for pat in forbidden:
                bad = [n for n in nets[net] if n.startswith(pat[:-1])] if pat.endswith("*") else ([pat] if pat in nets[net] else [])
                if bad:
                    errors.append(f"{net}: 不应出现 {bad}")
        elif forbidden == set() and nets[net] != must:
            errors.append(f"{net}: 额外节点 {sorted(nets[net] - must)}")
    # 2. 去耦电容在电源轨上
    for ref in DECAP_REFS:
        if not any(f"{ref}.1" in nets.get(n, set()) for n in ("+3V3",)):
            errors.append(f"去耦 {ref}.1 不在 +3V3 上")
        if not any(f"{ref}.2" in nets.get("GND", set()) for n in ("GND",)):
            errors.append(f"去耦 {ref}.2 不在 GND 上")
    # 3. 悬空网络(除豁免)
    for name, nodes in nets.items():
        if len(nodes) < 2 and name not in DNP_NETS and not name.startswith("unconnected-"):
            errors.append(f"悬空网络 {name}: {sorted(nodes)}")
    # 4. GPIO 网络: U1 + 恰好一个排针引脚
    j_pins = {n for net in nets.values() for n in net if n.startswith(("J1.", "J2."))}
    for name, nodes in nets.items():
        import re as _re
        if _re.fullmatch(r"P[A-K]\d+(_C)?", name):
            u1n = [n for n in nodes if n.startswith("U1.")]
            hn = [n for n in nodes if n.startswith(("J1.", "J2."))]
            if not u1n:
                errors.append(f"GPIO {name}: 无 U1 节点")
            if len(hn) != 1 and name not in ("PB0", "PC13", "PA13", "PA14", "PB3"):
                errors.append(f"GPIO {name}: 排针节点数 {len(hn)} ({hn})")
    # 5. U2 的 EN 应悬空(SS 已按 TI 建议外接 CSS)
    for n, nodes in nets.items():
        if "U2.3" in nodes and n != "EN":
            errors.append(f"U2.3 出现在网络 {n}")

    print(f"网络总数: {len(nets)}")
    if errors:
        print(f"\\n✗ 门禁失败, {len(errors)} 处:")
        for e in errors[:40]:
            print("  -", e)
        sys.exit(1)
    print("✓ 网表门禁全部通过")


if __name__ == "__main__":
    main()
