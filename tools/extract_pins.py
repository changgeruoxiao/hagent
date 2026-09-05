#!/usr/bin/env python3
"""提取 STM32H743ZITx 引脚定义并与 DS12110 数据手册交叉核对。

用法:
    python extract_pins.py            # 打印符号库电源/特殊引脚 + 数据手册对照行
"""
import re
import sys
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
SYM_LIB = Path(r"C:\Users\27417\AppData\Local\Programs\KiCad\10.0\share\kicad\symbols\MCU_ST_STM32H7.kicad_sym")
DS_PDF = WS / "doc" / "DS12110_STM32H743xI_数据手册.pdf"
SYMBOL_NAME = "STM32H743ZITx"

# 数据手册 pin table 中需要核对的信号（含 KiCad 符号里的常见写法）
SPECIAL = re.compile(
    r"^(VDD|VSS|VDDA|VSSA|VREF|VBAT|VCAP|PDR_ON|NRST|BOOT0|VDDUSB|VDDSDMMC|PH0|PH1|PC14|PC15|PA13|PA14|PB3|PA11|PA12|PC13|PB0)$"
)


def pins_from_symbol():
    """从 KiCad 符号库解析 STM32H743ZITx 的 (number, name) 列表。"""
    from kiutils.symbol import SymbolLib

    lib = SymbolLib.from_file(str(SYM_LIB))
    sym = next(s for s in lib.symbols if s.entryName == SYMBOL_NAME)
    pins = {}
    for unit in sym.units:
        for p in unit.pins or []:
            pins[int(p.number)] = p.name
    return pins


def dump_symbol(pins):
    special = {n: name for n, name in sorted(pins.items()) if SPECIAL.match(name)}
    gpio = {n: name for n, name in pins.items() if re.match(r"^P[A-K]\d+$", name)}
    print(f"=== KiCad 符号 {SYMBOL_NAME}: 共 {len(pins)} 引脚, GPIO {len(gpio)} 个 ===")
    print("--- 电源/特殊引脚 (pin: name) ---")
    for n, name in special.items():
        print(f"  {n:3d}: {name}")
    return special


def dump_datasheet(sym_pins):
    """用 DS12110 的 LQFP144 引脚图(Figure)图注做全脚交叉核对。

    图注文本为 "名字 数字"(左列) 与 "数字 名字"(右列) 相邻对, 比多列引脚表
    的文本提取可靠得多。VDD33_USB(符号) 与 VDD33USB(手册) 去下划线后归一。
    """
    from pypdf import PdfReader

    reader = PdfReader(str(DS_PDF))
    pages = [i for i, p in enumerate(reader.pages)
             if "VCAP" in (p.extract_text() or "") and "LQFP144" in (p.extract_text() or "")]
    vocab = {n.replace("_", ""): n for n in sym_pins.values()} | {"VREF+": "VREF+"}
    num_re = re.compile(r"^\d{1,3}$")
    fig = {}
    for i in pages:
        toks = (reader.pages[i].extract_text() or "").split()
        for a, b in zip(toks, toks[1:]):
            for name, num in ((a, b), (b, a)):
                if name in vocab and num_re.match(num) and 1 <= int(num) <= 144:
                    fig.setdefault(int(num), set()).add(
                        vocab[name].replace("_", ""))
    print(f"\n=== DS12110 LQFP144 引脚图交叉核对: 图注覆盖 {len(fig)}/144 ===")
    ok = conflict = missing = 0
    for n in sorted(sym_pins):
        got = fig.get(n)
        want = sym_pins[n].replace("_", "")
        if not got:
            missing += 1
        elif want in got:
            ok += 1
        else:
            conflict += 1
            print(f"  !! pin{n}: 符号={sym_pins[n]}  图注={got}")
    print(f"一致 {ok} / 冲突 {conflict} / 图注未覆盖 {missing}")
    # 单独确认关键特殊脚
    for probe in (95, 71, 106, 143, 138):
        print(f"  关键脚 pin{probe}: 图注={fig.get(probe)}  符号={sym_pins.get(probe)}")
    return fig


if __name__ == "__main__":
    pins = pins_from_symbol()
    dump_symbol(pins)
    # 额外输出: 非GPIO且未归入电源表的引脚(查漏)
    leftovers = {n: name for n, name in sorted(pins.items())
                 if not SPECIAL.match(name) and not re.match(r"^P[A-K]\d+$", name)}
    if leftovers:
        print("--- 未归类引脚(查漏) ---")
        for n, name in leftovers.items():
            print(f"  {n:3d}: {name}")
    try:
        dump_datasheet(pins)
    except Exception as e:
        print(f"数据手册提取失败: {e}", file=sys.stderr)
