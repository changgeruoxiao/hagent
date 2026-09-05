#!/usr/bin/env python3
"""KiCad 原理图(.kicad_sch)生成框架。

直接操作 S-expression, 不依赖 kiutils API。核心能力:
- 从官方符号库提取符号定义块(原文嵌入 lib_symbols)与引脚几何
- 符号实例放置(支持 90° 旋转), 引脚世界坐标/引出线方向计算
- 走线 / 网络标签 / 电源端口辅助函数
坐标约定: 原理图原点左上, x 向右, y 向下, 单位 mm。
"""
from __future__ import annotations

import math
import re
import uuid as uuidlib
from dataclasses import dataclass
from pathlib import Path

from project_config import SYMBOLS as KICAD_SYM_DIR, REVISION
FILE_VERSION = 20231120
GEN_VERSION = "8.0"


# ---------------------------------------------------------------- 原子与序列化
class Q(str):
    """强制加引号的字符串。"""
    __slots__ = ()


class U(str):
    """强制不加引号的原子。"""
    __slots__ = ()


_UNQUOTED = {"yes", "no", "default", "solid", "dashed", "dot", "dash_dot",
             "left", "right", "top", "bottom", "mirror", "input", "output",
             "bidirectional", "tri_state", "passive", "power_in", "power_out",
             "unspecified", "unconnected", "free", "nan"}


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def dump_atom(x, is_key=False) -> str:
    if isinstance(x, U):
        return str(x)
    if isinstance(x, Q):
        return f'"{_esc(x)}"'
    if is_key:
        return str(x)
    s = str(x)
    if re.fullmatch(r"-?\d+(\.\d+)?", s) or s in _UNQUOTED:
        return s
    return f'"{_esc(s)}"'


def sexp(e, indent=0) -> str:
    if not isinstance(e, list):
        return dump_atom(e)
    inner = " ".join(dump_atom(x, i == 0) if not isinstance(x, list) else sexp(x) for i, x in enumerate(e))
    return "(" + inner + ")"


def fmt(v: float) -> str:
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s if s else "0"


def u5(name: str) -> str:
    return str(uuidlib.uuid5(uuidlib.NAMESPACE_URL, "hagent.sch/" + name))


# ---------------------------------------------------------------- S-expr 解析
def _tokenize(text: str):
    toks, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
        elif c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            toks.append("S" + text[i + 1:j].replace('\\"', '"'))
            i = j + 1
        elif c in "()":
            toks.append(c); i += 1
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in '()"':
                j += 1
            toks.append("A" + text[i:j]); i = j
    return toks


def parse(text: str):
    toks, pos = _tokenize(text), [0]

    def rec():
        t = toks[pos[0]]
        if t == "(":
            pos[0] += 1
            lst = []
            while toks[pos[0]] != ")":
                lst.append(rec())
            pos[0] += 1
            return lst
        pos[0] += 1
        return t[1:]  # 去掉 S/A 前缀

    return rec()


# ---------------------------------------------------------------- 符号库
@dataclass
class Pin:
    number: str
    name: str
    unit: int
    x: float
    y: float
    angle: int    # 引脚图形方向(KiCad 角度): 0=图形向右
    etype: str


class LibSymbol:
    def __init__(self, lib_nick: str, name: str, block_text: str):
        self.lib_id = f"{lib_nick}:{name}"
        self.name = name
        # lib_symbols 条目名必须带库昵称前缀(子块保持原名)
        self.block_text = block_text.replace(f'(symbol "{name}"', f'(symbol "{self.lib_id}"', 1)
        self.expr = parse(block_text)
        self.extends = next((x[1] for x in self.expr
                             if isinstance(x, list) and x and x[0] == "extends"), None)
        self.pins: list[Pin] = []
        self._walk(self.expr, name, unit=0)

    def _walk(self, expr, sym_name, unit):
        for item in expr:
            if not (isinstance(item, list) and item):
                continue
            if item[0] == "pin":
                at = next(x for x in item if isinstance(x, list) and x[0] == "at")
                name_e = next(x for x in item if isinstance(x, list) and x[0] == "name")
                num_e = next(x for x in item if isinstance(x, list) and x[0] == "number")
                ang = int(float(at[3])) if len(at) > 3 else 0
                self.pins.append(Pin(num_e[1], name_e[1], unit, float(at[1]), float(at[2]), ang, item[1]))
            elif item[0] == "symbol":
                m = re.match(rf"^{re.escape(sym_name)}_(\d+)_(\d+)$", item[1])
                if m:
                    self._walk(item, sym_name, unit=int(m.group(1)))

    def pins_of_unit(self, unit: int) -> list[Pin]:
        return [p for p in self.pins if p.unit in (0, unit)]

    def pin(self, number: str) -> Pin:
        return next(p for p in self.pins if p.number == number)

    @property
    def n_units(self) -> int:
        return max((p.unit for p in self.pins), default=0) or 1


class LibCache:
    _libs: dict = {}
    _symbols: dict = {}

    @classmethod
    def get(cls, lib_nick: str) -> dict:
        if lib_nick not in cls._libs:
            text = (KICAD_SYM_DIR / f"{lib_nick}.kicad_sym").read_text(encoding="utf-8")
            blocks = {}
            for m in re.finditer(r'\(symbol "([^"]+)"', text):
                nm = m.group(1)
                if re.search(r"_\d+_\d+$", nm):
                    continue
                start, depth, j = m.start(), 0, m.start()
                while j < len(text):
                    if text[j] == "(":
                        depth += 1
                    elif text[j] == ")":
                        depth -= 1
                        if depth == 0:
                            break
                    j += 1
                blocks[nm] = text[start:j + 1]
            cls._libs[lib_nick] = blocks
        return cls._libs[lib_nick]

    @classmethod
    def load(cls, lib_id: str) -> LibSymbol:
        nick, name = lib_id.split(":")
        if lib_id not in cls._symbols:
            # Only parse the requested symbol. Parentheses inside quoted descriptions
            # are text, not scope delimiters (old full-library scan could take minutes).
            text = (KICAD_SYM_DIR / f"{nick}.kicad_sym").read_text(encoding="utf-8")
            start = text.index(f'(symbol "{name}"')
            depth = 0
            for token in re.finditer(r'"(?:[^"\\]|\\.)*"|[()]', text[start:]):
                if token.group() == '(':
                    depth += 1
                elif token.group() == ')':
                    depth -= 1
                    if depth == 0:
                        cls._symbols[lib_id] = LibSymbol(nick, name, text[start:start + token.end()])
                        break
            else:
                raise ValueError(f'Unclosed library symbol: {lib_id}')
        return cls._symbols[lib_id]


def custom_symbol(lib_id: str, block_text: str) -> LibSymbol:
    nick, name = lib_id.split(":")
    return LibSymbol(nick, name, block_text)


# ---------------------------------------------------------------- 放置与变换
def _rot(dx: float, dy: float, ang: int):
    a = math.radians(ang)
    return dx * math.cos(a) + dy * math.sin(a), -dx * math.sin(a) + dy * math.cos(a)


DIR_VEC = {0: (1, 0), 90: (0, -1), 180: (-1, 0), 270: (0, 1)}  # 引脚图形方向(伸向本体)


@dataclass
class Instance:
    lib: LibSymbol
    ref: str
    value: str
    footprint: str
    x: float
    y: float
    angle: int = 0
    unit: int = 1
    datasheet: str = "~"
    dnp: bool = False
    uuid: str = ""

    def pin_pos(self, number: str):
        p = self.lib.pin(number)
        dx, dy = _rot(p.x, -p.y, self.angle)
        return self.x + dx, self.y + dy

    def pin_dir(self, number: str):
        """引脚外向方向(走线应走的方向) = 图形方向取反, 再随实例旋转。"""
        p = self.lib.pin(number)
        v = DIR_VEC[p.angle % 360]
        dx, dy = _rot(-v[0], -v[1], self.angle)
        return (round(dx), round(dy))


class SchBuilder:
    def __init__(self, title: str, paper: str = "A2", project: str = "board"):
        self.title, self.paper, self.project = title, paper, project
        self.root_uuid = u5("root")
        self.symbols: list[Instance] = []
        self.custom_blocks: dict[str, str] = {}
        self._libs: dict[str, LibSymbol] = {}
        self.wires: list = []
        self.junctions: list = []
        self.labels: list = []
        self.powers: list = []
        self.notes: list = []
        self._pwr_count = 0

    def lib(self, lib_id: str, custom_block: str | None = None) -> LibSymbol:
        if lib_id not in self._libs:
            sym = custom_symbol(lib_id, custom_block) if custom_block else LibCache.load(lib_id)
            # extends 派生符号: 拍平为独立定义(嵌入 extends 条目时 KiCad 可能无法解析引脚)
            if sym.extends:
                nick = lib_id.split(":")[0]
                parent = LibCache.load(f"{nick}:{sym.extends}")
                sym.pins = parent.pins
                sym.block_text = self._flatten(sym, parent)
            self._libs[lib_id] = sym
            if custom_block:
                self.custom_blocks[lib_id] = custom_block
        return self._libs[lib_id]

    @staticmethod
    def _flatten(sym: LibSymbol, parent: LibSymbol) -> str:
        """派生符号 + 父符号图形/引脚子块 → 独立定义(去掉 extends)。"""
        import re as _re
        blk = _re.sub(r"\(extends \"[^\"]*\"\)\s*", "", sym.block_text, count=1)
        subs = []
        for m in _re.finditer(r'\(symbol "', parent.block_text):
            name = _re.match(r'\(symbol "([^"]+)"', parent.block_text[m.start():]).group(1)
            if _re.search(r"_\d+_\d+$", name):
                start, depth, j = m.start(), 0, m.start()
                text = parent.block_text
                while j < len(text):
                    if text[j] == "(":
                        depth += 1
                    elif text[j] == ")":
                        depth -= 1
                        if depth == 0:
                            break
                    j += 1
                sub = text[start:j + 1]
                # 子块名必须与本符号名一致: PARENT_x_y -> DERIVED_x_y
                sub = sub.replace(f'(symbol "{parent.name}_', f'(symbol "{sym.name}_', 1)
                subs.append(sub)
        if subs:
            blk = blk.rstrip()[:-1] + "\n" + "\n".join(subs) + ")"
        return blk

    def place(self, lib_id, ref, value, footprint, x, y, angle=0, unit=1,
              custom_block=None, datasheet="~", dnp=False, val_off=(0, 2.54)) -> Instance:
        self.lib(lib_id, custom_block)
        inst = Instance(self._libs[lib_id], ref, value, footprint, x, y, angle, unit, datasheet, dnp,
                        u5(f"{ref}#{unit}"))
        inst.val_off = val_off
        self.symbols.append(inst)
        return inst

    def wire(self, *pts):
        self.wires.append([(round(float(x), 4), round(float(y), 4)) for x, y in pts])

    def junction(self, x, y):
        self.junctions.append((round(float(x), 4), round(float(y), 4)))

    def rail(self, points, port_net=None, port_idx=0):
        """汇流排: 各点竖直接入公共横轨, T 型交叉处加结点, 可选单端电源口。"""
        ys = [p[1] for p in points]
        rail_y = min(ys) - 10.16
        xs = sorted(p[0] for p in points)
        for px, py in points:
            self.wire((px, py), (px, rail_y))
            self.junction(px, rail_y)
        self.wire((xs[0], rail_y), (xs[-1], rail_y))
        if port_net:
            self.power(port_net, xs[0], rail_y)
        return rail_y

    def stub(self, inst: Instance, pin: str, length=2.54):
        px, py = inst.pin_pos(pin)
        dx, dy = inst.pin_dir(pin)
        ex, ey = round(px + dx * length, 4), round(py + dy * length, 4)
        self.wire((px, py), (ex, ey))
        return ex, ey

    def pin_label(self, inst: Instance, pin: str, net: str, length=2.54):
        ex, ey = self.stub(inst, pin, length)
        dx, dy = inst.pin_dir(pin)
        side = {(1, 0): "right", (-1, 0): "left", (0, -1): "up", (0, 1): "down"}[(dx, dy)]
        self.labels.append((net, ex, ey, side))

    def pin_power(self, inst: Instance, pin: str, net: str, length=2.54):
        ex, ey = self.stub(inst, pin, length)
        self.power(net, ex, ey)

    def power(self, net, x, y):
        assert net in ("GND", "+3V3", "+5V"), f"未支持的网络 {net}"
        self.lib(f"power:{net}")
        self.powers.append((net, round(float(x), 4), round(float(y), 4)))

    def note(self, text, x, y, size=1.5):
        self.notes.append((text, x, y, size))

    # ---- 序列化 ----
    def _item_wire(self, w):
        pts = [["xy", fmt(p[0]), fmt(p[1])] for p in w]
        return ["wire", ["pts"] + pts, ["stroke", ["width", "0"], ["type", "default"]],
                ["uuid", u5("w" + repr(w))]]

    def _label(self, text, x, y, side):
        just_r = side in ("left", "down")
        ang = {"right": 0, "left": 0, "up": 90, "down": 270}[side]
        return ["label", Q(text), ["at", fmt(x), fmt(y), str(ang)],
                ["effects", ["font", ["size", "1.27", "1.27"]], ["justify", "right" if just_r else "left",
                 "bottom" if side == "up" else ("top" if side == "down" else "bottom")]],
                ["uuid", u5(f"lbl/{text}/{x}/{y}")]]

    def _symbol(self, inst: Instance):
        e = ["symbol", ["lib_id", Q(inst.lib.lib_id)],
             ["at", fmt(inst.x), fmt(inst.y), str(inst.angle)],
             ["unit", str(inst.unit)], ["exclude_from_sim", "no"], ["in_bom", "yes"],
             ["on_board", "yes"], ["dnp", "yes" if inst.dnp else "no"], ["uuid", inst.uuid],
             ["property", Q("Reference"), Q(inst.ref), ["at", fmt(inst.x), fmt(inst.y - 2.54), "0"],
              ["effects", ["font", ["size", "1.27", "1.27"]], ["justify", "left", "bottom"]]],
             ["property", Q("Value"), Q(inst.value),
              ["at", fmt(inst.x + getattr(inst, "val_off", (0, 2.54))[0]),
               fmt(inst.y + getattr(inst, "val_off", (0, 2.54))[1]), "0"],
              ["effects", ["font", ["size", "1.27", "1.27"]], ["justify", "left", "top"]]],
             ["property", Q("Footprint"), Q(inst.footprint), ["at", fmt(inst.x), fmt(inst.y), "0"],
              ["effects", ["font", ["size", "1.27", "1.27"]], ["hide", "yes"]]],
             ["property", Q("Datasheet"), Q(inst.datasheet), ["at", fmt(inst.x), fmt(inst.y), "0"],
              ["effects", ["font", ["size", "1.27", "1.27"]], ["hide", "yes"]]]]
        for p in inst.lib.pins_of_unit(inst.unit):
            e.append(["pin", Q(p.number), ["uuid", u5(f"{inst.ref}/{inst.unit}/{p.number}")]])
        e.append(["instances", ["project", Q(self.project),
                  ["path", "/" + self.root_uuid, ["reference", Q(inst.ref)], ["unit", str(inst.unit)]]]])
        return e

    def _power(self, net, x, y, idx):
        return ["symbol", ["lib_id", Q(f"power:{net}")], ["at", fmt(x), fmt(y), "0"], ["unit", "1"],
                ["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "yes"], ["dnp", "no"],
                ["uuid", u5(f"pwr/{net}/{x}/{y}")],
                ["property", Q("Reference"), Q(f"#PWR{idx:04d}"), ["at", fmt(x), fmt(y - 1.27), "0"],
                 ["hide", "yes"],
                 ["effects", ["font", ["size", "1.27", "1.27"]], ["justify", "bottom"]]],
                ["property", Q("Value"), Q(net), ["at", fmt(x), fmt(y), "0"],
                 ["effects", ["font", ["size", "1.27", "1.27"]]]],
                ["pin", Q("1"), ["uuid", u5(f"pwrpin/{net}/{x}/{y}")]],
                ["instances", ["project", Q(self.project),
                 ["path", "/" + self.root_uuid, ["reference", Q(f"#PWR{idx:04d}")], ["unit", "1"]]]]]

    def write(self, path) -> str:
        header = [
            ["version", str(FILE_VERSION)], ["generator", "hagent"], ["generator_version", Q(GEN_VERSION)],
            ["uuid", self.root_uuid], ["paper", Q(self.paper)],
            ["title_block", ["title", Q(self.title)], ["date", Q("2026-09-05")], ["rev", Q(REVISION)]]]
        lines = ["(kicad_sch " + " ".join(sexp(h) for h in header)]
        # lib_symbols 原文嵌入
        lib_lines = ["  (lib_symbols"]
        for sym in self._libs.values():
            for blk in sym.block_text.splitlines():
                lib_lines.append("  " + blk)
        lib_lines.append("  )")
        lines.extend(lib_lines)
        idx = 0
        for w in self.wires:
            lines.append("  " + sexp(self._item_wire(w)))
        for jx, jy in self.junctions:
            lines.append("  " + sexp(["junction", ["at", fmt(jx), fmt(jy)], ["diameter", "0"],
                        ["color", "0", "0", "0", "0"], ["uuid", u5(f"jct/{jx}/{jy}")]]))
        for net, x, y in self.powers:
            idx += 1
            lines.append("  " + sexp(self._power(net, x, y, idx)))
        for text, x, y, side in self.labels:
            lines.append("  " + sexp(self._label(text, x, y, side)))
        for inst in self.symbols:
            lines.append("  " + sexp(self._symbol(inst)))
        for text, x, y, size in self.notes:
            lines.append("  " + sexp(["text", Q(text), ["at", fmt(x), fmt(y), "0"],
                        ["effects", ["font", ["size", fmt(size), fmt(size)]], ["justify", "left", "top"]],
                        ["uuid", u5(f"note/{text}/{x}/{y}")]]))
        lines.append("  " + sexp(["sheet_instances", ["path", "/", ["page", Q("1")]]]))
        lines.append(")")
        out = "\n".join(lines) + "\n"
        Path(path).write_text(out, encoding="utf-8")
        return out
