#!/usr/bin/env python3
"""最小冒烟测试: 验证 sch_build 生成的文件可被 kicad-cli 解析。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sch_build import SchBuilder, LibCache

b = SchBuilder("冒烟测试", paper="A4", project="smoke")

# 电阻: pin1 -> +3V3, pin2 -> 标签 PA0
r1 = b.place("Device:R", "R1", "10k", "Resistor_SMD:R_0402_1005Metric", 100, 60)
b.pin_power(r1, "1", "+3V3")
b.pin_label(r1, "2", "PA0")

# 电容(旋转90°): pin1 -> +3V3, pin2 -> GND, 验证角度变换
c1 = b.place("Device:C", "C1", "100nF", "Capacitor_SMD:C_0402_1005Metric", 100, 90, angle=270)
b.pin_power(c1, "1", "+3V3")
b.pin_power(c1, "2", "GND")

out = b.write(Path(__file__).parents[1] / "kicad" / "smoke.kicad_sch")
print("已生成 smoke.kicad_sch,", len(out.splitlines()), "行")
print("R1 引脚位置: pin1", r1.pin_pos("1"), "pin2", r1.pin_pos("2"))
print("C1 引脚位置(270°): pin1", c1.pin_pos("1"), "pin2", c1.pin_pos("2"))
