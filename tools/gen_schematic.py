#!/usr/bin/env python3
"""STM32H743ZIT6 核心板原理图生成器(依据《STM32H743ZIT6_核心板设计规格书》§2-§7 与附录A)。

产物: kicad/stm32h743_core.kicad_sch
坐标: A2 图纸(594x420mm), 原点左上。
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sch_build import SchBuilder, LibCache
from project_config import OUT

WS = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------- 封装常量
FP = {
    "R": "Resistor_SMD:R_0402_1005Metric",
    "C": "Capacitor_SMD:C_0402_1005Metric",
    "C0603": "Capacitor_SMD:C_0603_1608Metric",
    "C0805": "Capacitor_SMD:C_0805_2012Metric",
    "C1206": "Capacitor_SMD:C_1206_3216Metric",
    "L": "Inductor_SMD:L_Bourns_SRP7028A_7.3x6.6mm",
    "FB": "Inductor_SMD:L_0603_1608Metric",
    "D": "Diode_SMD:D_SMA",
    "F": "Fuse:Fuse_1206_3216Metric",
    "LED": "LED_SMD:LED_0603_1608Metric",
    "SW": "Button_Switch_THT:SW_PUSH_6mm",
    "USBC": "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
    "ESD": "Package_TO_SOT_SMD:SOT-23-6",
    "DCDC": "Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.29x3mm",
    "MCU": "Package_QFP:LQFP-144_20x20mm_P0.5mm",
    "H228": "Connector_PinHeader_2.54mm:PinHeader_2x28_P2.54mm_Vertical",
    "H106": "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical",
    "H103": "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
    "H102": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
}

# ---------------------------------------------------------------- TPS54331 自建符号
TPS54331_BLOCK = '''(symbol "TPS54331DDA"
	(pin_names (offset 1.016))
	(in_bom yes) (on_board yes)
	(property "Reference" "U" (at 0 13.97 0) (effects (font (size 1.27 1.27))))
	(property "Value" "TPS54331DDA" (at 0 -13.97 0) (effects (font (size 1.27 1.27))))
	(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
	(property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
	(symbol "TPS54331DDA_0_1"
		(rectangle (start -7.62 11.43) (end 7.62 -11.43)
			(stroke (width 0.254) (type default)) (fill (type background)))
	)
	(symbol "TPS54331DDA_1_1"
		(pin output line (at -12.7 7.62 0) (length 5.08)
			(name "BOOT" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
		(pin power_in line (at -12.7 2.54 0) (length 5.08)
			(name "VIN" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
		(pin input line (at -12.7 -2.54 0) (length 5.08)
			(name "EN" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
		(pin input line (at -12.7 -7.62 0) (length 5.08)
			(name "SS" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
		(pin input line (at 12.7 7.62 180) (length 5.08)
			(name "VSENSE" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
		(pin output line (at 12.7 2.54 180) (length 5.08)
			(name "COMP" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
		(pin power_in line (at 12.7 -2.54 180) (length 5.08)
			(name "GND" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))
		(pin output line (at 12.7 -7.62 180) (length 5.08)
			(name "PH" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))
		(pin power_in line (at 0 -16.51 90) (length 5.08)
			(name "EP" (effects (font (size 1.27 1.27)))) (number "9" (effects (font (size 1.27 1.27)))))
	)
)'''

# ---------------------------------------------------------------- MCU 引脚→网络规则(附录A)
POWER_NETS = ("GND", "+3V3", "+5V")

def mcu_net(num: int, name: str) -> str:
    if name == "VCAP":
        return "VCAP"  # AN4938 Rev7 §2.2 + MB1364E sheet 4: tie both pins, local 2.2uF each.
    if name in ("VDD", "VDD33_USB"):
        return "+3V3"
    if name in ("VSS", "VSSA"):
        return "GND"
    return {"VDDA": "VDDA", "VREF+": "VREF+", "VBAT": "VBAT", "PDR_ON": "PDR_ON",
            "NRST": "NRST", "BOOT0": "BOOT0", "PH0": "OSC_IN", "PH1": "OSC_OUT",
            "PC14": "OSC32_IN", "PC15": "OSC32_OUT",
            "PA11": "USB_DM", "PA12": "USB_DP"}.get(name, name)

SWD_GPIO = {"PA13", "PA14", "PB3"}          # 专用 SWD, 不上排针
USB_GPIO = {"PA11", "PA12"}                  # 专用 USB
OSC_GPIO = {"PC14", "PC15", "PH0", "PH1"}    # 晶振占用


def conn(b, inst, pin, net, len_lbl=3.81, len_pwr=5.08):
    if net in POWER_NETS:
        b.pin_power(inst, pin, net, len_pwr)
    else:
        b.pin_label(inst, pin, net, len_lbl)


def two_pin(b, lib_id, ref, val, fp, x, y, net1, net2, angle=0, dnp=False):
    inst = b.place(lib_id, ref, val, fp, x, y, angle=angle, dnp=dnp)
    conn(b, inst, "1", net1)
    conn(b, inst, "2", net2)
    return inst


def rc(b, ref, val, fp, x, y, top, bot):
    """竖直两端器件(R/C 默认 pin1 上 pin2 下)。"""
    return two_pin(b, {"R": "Device:R", "C": "Device:C"}[ref[0]], ref, val, fp, x, y, top, bot)


def build():
    b = SchBuilder("STM32H743ZIT6 核心板(最小系统)", paper="A2", project="stm32h743_core")
    mcu_lib = LibCache.load("MCU_ST_STM32H7:STM32H743ZITx")

    # ================= MCU =================
    u1 = b.place("MCU_ST_STM32H7:STM32H743ZITx", "U1", "STM32H743ZIT6", FP["MCU"], 270, 140)
    mcu_pins = {int(p.number): p for p in mcu_lib.pins}  # 按引脚号去重
    drawn = {}  # 世界坐标 -> 网络; 同坐标只画一次引线(符号内同名电源脚叠画)
    rail_pts = []
    for num in sorted(mcu_pins):
        net = mcu_net(num, mcu_pins[num].name)
        pos = tuple(round(v, 2) for v in u1.pin_pos(str(num)))
        if pos in drawn:
            assert drawn[pos] == net, f"坐标 {pos} 上不同网络叠加: {drawn[pos]} vs {net}"
            continue
        drawn[pos] = net
        if net == "+3V3" and u1.pin_dir(str(num)) == (0, -1):
            rail_pts.append(pos)      # 顶部 VDD 群走汇流排
            continue
        conn(b, u1, str(num), net)
    b.rail(rail_pts, "+3V3")

    gpio = sorted({p.name for num, p in mcu_pins.items()
                   if re.fullmatch(r"P[A-K]\d+(_C)?", p.name)
                   and p.name not in SWD_GPIO | USB_GPIO | OSC_GPIO
                   and mcu_net(num, p.name) == p.name},
                  key=lambda n: (n[1], n[2:].rstrip("_C"), len(n)))
    assert len(gpio) == 105, f"GPIO 数量异常: {len(gpio)}"

    # ================= 电源输入与 DCDC (左上) =================
    b.note("电源输入与DCDC", 25, 20, 2)
    # USB-C 与 5VIN 输入合路
    j3 = b.place("Connector:USB_C_Receptacle_USB2.0_16P", "J3", "USB_C", FP["USBC"], 35, 100)
    drawn = set()  # 该符号多个电源脚共享同一坐标, 每个坐标只画一次引线
    for p in j3.lib.pins:
        nm = p.name.split("/")[-1]
        net = {"GND": "GND", "VBUS": "VBUS", "CC1": "CC1", "CC2": "CC2",
               "D+": "USB_DP_P", "D-": "USB_DM_P", "SHIELD": "GND"}.get(nm)
        if not net:
            continue
        pos = tuple(round(v, 2) for v in j3.pin_pos(p.number))
        if pos in drawn:
            continue
        drawn.add(pos)
        conn(b, j3, p.number, net)
    two_pin(b, "Device:R", "R10", "5.1k", FP["R"], 75, 95, "CC1", "GND")
    two_pin(b, "Device:R", "R11", "5.1k", FP["R"], 85, 95, "CC2", "GND")
    # USB 后级: 保险丝 → 二极管合路(电流方向: 输入→+5V, 故 K 极朝 +5V)
    two_pin(b, "Device:Polyfuse", "F1", "500mA", FP["F"], 100, 70, "VBUS", "VBUS_F")
    two_pin(b, "Device:D_Schottky", "D5", "SS34", FP["D"], 120, 70, "+5V", "VBUS_F")
    j6 = b.place("Connector_Generic:Conn_01x02", "J6", "5VIN", FP["H102"], 25, 60)
    conn(b, j6, "1", "5VIN")
    conn(b, j6, "2", "GND")
    two_pin(b, "Device:D_Schottky", "D6", "SS34", FP["D"], 120, 60, "+5V", "5VIN")
    # VBUS 检测分压(DNP, 默认不装)
    two_pin(b, "Device:R", "R12", "68k", FP["R"], 150, 95, "VBUS", "VBUS_SENSE", dnp=True)
    two_pin(b, "Device:R", "R13", "100k", FP["R"], 160, 95, "VBUS_SENSE", "GND", dnp=True)
    # DCDC 主芯片
    u2 = b.place("hagent:TPS54331DDA", "U2", "TPS54331DDAR", FP["DCDC"], 55, 55,
                 custom_block=TPS54331_BLOCK, val_off=(0, 18.5))
    for pin, net in {"1": "BOOT", "2": "+5V", "5": "FB", "6": "COMP", "7": "GND", "8": "PH", "9": "GND"}.items():
        conn(b, u2, pin, net)
    two_pin(b, "Device:C", "C20", "100n", FP["C"], 48, 25, "+5V", "GND")          # 输入
    two_pin(b, "Device:C", "C21", "10uF", FP["C0805"], 35, 45, "+5V", "GND")
    two_pin(b, "Device:C", "C22", "10uF", FP["C0805"], 35, 60, "+5V", "GND")
    two_pin(b, "Device:C", "C23", "100n", FP["C"], 95, 40, "BOOT", "PH")          # 自举
    two_pin(b, "Device:D_Schottky", "D7", "SS34", FP["D"], 95, 90, "PH", "GND")   # 续流(K上A下)
    two_pin(b, "Device:L", "L1", "6.8uH/4A", FP["L"], 120, 110, "PH", "3V3_SW")
    two_pin(b, "Device:R", "R14", "0R", "Resistor_SMD:R_0805_2012Metric", 145, 110, "3V3_SW", "+3V3")
    two_pin(b, "Device:C", "C24", "47uF", FP["C1206"], 160, 120, "3V3_SW", "GND")
    two_pin(b, "Device:C", "C25", "47uF", FP["C1206"], 168, 120, "3V3_SW", "GND")
    two_pin(b, "Device:R", "R15", "10.2k", FP["R"], 30, 150, "3V3_SW", "FB")  # Sense BEFORE removable current link.
    two_pin(b, "Device:R", "R16", "3.24k", FP["R"], 42, 162, "FB", "GND")
    two_pin(b, "Device:R", "R17", "29.4k", FP["R"], 95, 125, "COMP", "COMP_M")    # II 型补偿
    two_pin(b, "Device:C", "C26", "1nF", FP["C"], 105, 138, "COMP_M", "GND")
    two_pin(b, "Device:C", "C27", "47pF", FP["C"], 85, 138, "COMP", "GND")

    # ================= USB ESD (右上) =================
    b.note("USB(ESD保护)", 340, 20, 2)
    u3 = b.place("Power_Protection:USBLC6-2SC6", "U3", "USBLC6-2SC6", FP["ESD"], 400, 55)
    for pin, net in {"1": "USB_DP", "3": "USB_DM", "4": "USB_DM_P", "5": "VBUS",
                     "6": "USB_DP_P", "2": "GND"}.items():
        conn(b, u3, pin, net)

    # ================= 去耦与特殊电源 (左中) =================
    b.note("MCU电源去耦(每VDD脚100nF就近+4.7uFx2, VCAPx2=2.2uF)", 25, 205, 2)
    col_x = [40, 70, 100, 130]
    row_y = [225, 240, 255, 270, 285, 300, 315]
    decap = [*[("100nF", FP["C"])] * 11, ("4.7uF", FP["C0603"]), ("4.7uF", FP["C0603"])]
    i = 0
    for val, fp in decap:
        rc(b, f"C{60 + i}", val, fp, col_x[i % 4], row_y[i // 4], "+3V3", "GND")
        i += 1
    rc(b, "C40", "2.2uF", FP["C0603"], 150, 320, "VCAP", "GND")
    rc(b, "C41", "2.2uF", FP["C0603"], 165, 320, "VCAP", "GND")
    rc(b, "C42", "1uF", FP["C0603"], 150, 340, "VDDA", "GND")
    rc(b, "C43", "100nF", FP["C"], 165, 340, "VDDA", "GND")
    rc(b, "C44", "1uF", FP["C0603"], 150, 360, "VREF+", "GND")
    rc(b, "C45", "100n", FP["C"], 165, 360, "VREF+", "GND")
    rc(b, "C46", "1uF", FP["C0603"], 180, 320, "+3V3", "GND")      # VDD33_USB
    rc(b, "C47", "100n", FP["C"], 180, 340, "+3V3", "GND")
    two_pin(b, "Device:FerriteBead", "FB1", "600R@100MHz", FP["FB"], 180, 360, "+3V3", "VDDA")
    two_pin(b, "Device:R", "R20", "0R", FP["R"], 180, 378, "VDDA", "VREF+")
    two_pin(b, "Device:R", "R21", "0R", FP["R"], 40, 370, "+3V3", "VBAT")
    rc(b, "C48", "100nF", FP["C"], 90, 370, "VBAT", "GND")
    two_pin(b, "Device:R", "R22", "10k", FP["R"], 60, 370, "PDR_ON", "+3V3")

    # ================= 时钟 (下方左) =================
    b.note("时钟(HSE 8MHz / LSE 32.768kHz)", 25, 390, 2)
    two_pin(b, "Device:Crystal", "X1", "8MHz", "Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm", 40, 330, "OSC_IN", "OSC_OUT")
    two_pin(b, "Device:C", "C50", "18pF", FP["C"], 55, 318, "OSC_IN", "GND")
    two_pin(b, "Device:C", "C51", "18pF", FP["C"], 55, 342, "OSC_OUT", "GND")
    two_pin(b, "Device:Crystal", "X2", "32.768kHz", "Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm", 110, 330, "OSC32_IN", "OSC32_OUT")
    two_pin(b, "Device:C", "C52", "18pF", FP["C"], 125, 318, "OSC32_IN", "GND")
    two_pin(b, "Device:C", "C53", "18pF", FP["C"], 125, 342, "OSC32_OUT", "GND")

    # ================= 复位/启动/调试 (下方中) =================
    b.note("复位 / BOOT0 / SWD", 200, 390, 2)
    two_pin(b, "Switch:SW_Push", "SW1", "NRST_KEY", FP["SW"], 200, 330, "NRST", "GND")
    two_pin(b, "Device:C", "C54", "100nF", FP["C"], 218, 330, "NRST", "GND")
    two_pin(b, "Device:R", "R23", "100k", FP["R"], 236, 330, "BOOT0", "GND")
    j5 = b.place("Connector_Generic:Conn_01x03", "J5", "BOOT", FP["H103"], 258, 330)
    for pin, net in {"1": "+3V3", "2": "BOOT0", "3": "GND"}.items():
        conn(b, j5, pin, net)
    j4 = b.place("Connector_Generic:Conn_01x06", "J4", "SWD", FP["H106"], 285, 330)
    for pin, net in {"1": "+3V3", "2": "PA13", "3": "PA14", "4": "PB3", "5": "NRST", "6": "GND"}.items():
        conn(b, j4, pin, net)

    # ================= 指示与人机 (右侧下) =================
    b.note("指示与人机", 350, 200, 2)
    two_pin(b, "Device:R", "R24", "1k", FP["R"], 360, 220, "+3V3", "LED_PWR")
    two_pin(b, "Device:LED", "D8", "PWR_GREEN", FP["LED"], 360, 240, "GND", "LED_PWR")
    two_pin(b, "Device:R", "R25", "1k", FP["R"], 390, 220, "+3V3", "LED_USER")
    two_pin(b, "Device:LED", "D9", "USER_BLUE", FP["LED"], 390, 240, "PB0", "LED_USER")
    two_pin(b, "Switch:SW_Push", "SW2", "USER_KEY", FP["SW"], 420, 220, "PC13", "GND")
    two_pin(b, "Device:C", "C55", "100nF", FP["C"], 440, 220, "PC13", "GND")
    # 测试点
    for k, (ref, net) in enumerate([("TP1", "+3V3"), ("TP2", "GND"), ("TP3", "VCAP"),
                                    ("TP4", "NRST"), ("TP5", "BOOT0"), ("TP6", "3V3_SW")]):
        tp = b.place("Connector:TestPoint", ref, net, "TestPoint:TestPoint_Pad_D1.0mm", 460, 215 + k * 12)
        conn(b, tp, "1", net)

    # ================= IO 排针 (最右, 2x28 x2) =================
    b.note("IO扩展(全部GPIO, PA13/14/PB3=SWD, PA11/12=USB 除外)", 480, 20, 2)
    def header(ref, x, y, nets):
        h = b.place("Connector_Generic:Conn_02x28_Odd_Even", ref, "GPIO", FP["H228"], x, y)
        for pin, net in nets.items():
            conn(b, h, str(pin), net, len_lbl=3.81, len_pwr=3.81)
        return h
    j1_nets = {i + 1: gpio[i] for i in range(53)}
    j1_nets.update({54: "+3V3", 55: "GND", 56: "GND"})
    j2_nets = {i + 1: gpio[53 + i] for i in range(52)}
    j2_nets.update({53: "+3V3", 54: "+3V3", 55: "GND", 56: "GND"})
    header("J1", 520, 60, j1_nets)
    header("J2", 520, 165, j2_nets)

    return b


if __name__ == "__main__":
    b = build()
    # 自检: 引线段不得共线重叠(会意外并网)
    def seg(w):
        (x1, y1), (x2, y2) = w
        return (x1, y1, x2, y2)
    wires = sorted(b.wires, key=lambda w: (w[0][0], w[0][1], w[1][0], w[1][1]))
    bad = []
    for i in range(len(wires)):
        x1, y1, x2, y2 = seg(wires[i])
        for j in range(i + 1, len(wires)):
            a1, b1, a2, b2 = seg(wires[j])
            if a1 > x2 or (a1 == x1 and b1 > y2):
                break
            # 共线且区间重叠
            if abs(x1 - x2) < 1e-6 and abs(a1 - a2) < 1e-6 and abs(x1 - a1) < 1e-6:
                lo1, hi1 = sorted((y1, y2)); lo2, hi2 = sorted((b1, b2))
                if max(lo1, lo2) < min(hi1, hi2):
                    bad.append((wires[i], wires[j]))
            elif abs(y1 - y2) < 1e-6 and abs(b1 - b2) < 1e-6 and abs(y1 - b1) < 1e-6:
                lo1, hi1 = sorted((x1, x2)); lo2, hi2 = sorted((a1, a2))
                if max(lo1, lo2) < min(hi1, hi2):
                    bad.append((wires[i], wires[j]))
    if bad:
        print(f"!! {len(bad)} 处引线重叠:")
        for w1, w2 in bad[:10]:
            print("   ", w1, "<->", w2)
        sys.exit(1)
    out = OUT / "stm32h743_core.kicad_sch"
    out.parent.mkdir(parents=True, exist_ok=True)
    b.write(out)
    print(f"已生成 {out}")
    print(f"元件 {len(b.symbols)} 个, 走线 {len(b.wires)} 段, 标签 {len(b.labels)} 个, 电源口 {len(b.powers)} 个")
