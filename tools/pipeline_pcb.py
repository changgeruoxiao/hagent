#!/usr/bin/env python3
"""PCB 流水线编排(系统 python): DSN 电源类编辑 -> Freerouting 无头布线 -> SES 回写 -> DRC -> 制造文件。

用法: python tools/pipeline_pcb.py [--max-passes 25]
"""
import json
import subprocess
import sys
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
KI = Path(r"C:\Users\27417\AppData\Local\Programs\KiCad\10.0\bin")
FR_DIR = WS / "tools" / "freerouting"
JAVA = FR_DIR / "jdk-25.0.4.1+1-jre" / "bin" / "java.exe"
JAR = FR_DIR / "freerouting.jar"
DSN = WS / "kicad" / "stm32h743_core.dsn"
SES = WS / "kicad" / "stm32h743_core.ses"
PCB = WS / "kicad" / "stm32h743_core.kicad_pcb"

# 进电源类(0.3mm 线宽)的网络; GND 不入(走线 0.2mm 更易布通, 连通靠 In1 地平面)
# 层策略(规格书 §8): In1 仅 GND plane, In2 仅 +3V3 plane, 信号仅 F/B。
# (类名, 成员网, 线宽mm, 允许层); Default 兜底信号网。
from project_config import IN2_FORBIDDEN as _IN2F, POWER_WIDTH as _PW
LAYER_PLAN = [
    ("GND", ["GND"], 0.25, ["In1.Cu", "F.Cu", "B.Cu"]),
    ("P3V3", ["+3V3"], 0.30, ["In2.Cu", "F.Cu", "B.Cu"]),
    ("POW5", ["+5V", "VBUS", "VBUS_F", "5VIN", "PH", "3V3_SW", "BOOT"], 0.30, ["F.Cu", "B.Cu"]),
    ("SIG2", None, _PW, ["F.Cu", "In2.Cu", "B.Cu"]),
    ("Default", None, 0.20, ["F.Cu", "B.Cu"]),
]
# 兼容引用(旧脚本)
POWER_NETS = LAYER_PLAN[1][1] + LAYER_PLAN[2][1]


NL = chr(10)  # DSN 文本的真实换行


def edit_dsn_power_class():
    """按 LAYER_PLAN 把网络分入带 use_layer 约束的类(幂等: 已处理则跳过)。"""
    text = DSN.read_text(encoding='utf-8')
    if "(class GND " in text:
        print("DSN 层类已存在, 跳过")
        return
    i = text.find("(class kicad_default")
    assert i >= 0, "DSN 无 kicad_default 类"
    depth, j = 0, i
    while j < len(text):
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                break
        j += 1
    block = text[i:j + 1]
    ck = block.find("(circuit")
    head_tokens = block[:ck].split()[1:]
    tail = block[ck:]
    v0 = tail.find('"') + 1
    v1 = tail.find('"', v0)
    use_via = tail[v0:v1]
    buckets = {plan[0]: [] for plan in LAYER_PLAN}
    for tok in head_tokens:
        for name, members, _, _ in LAYER_PLAN:
            if members and tok in members:
                buckets[name].append(tok)
                break
        else:
            buckets['SIG2' if tok not in _IN2F else 'Default'].append(tok)
    new_blocks = ''
    for name, members, width, layers in LAYER_PLAN:
        nets = buckets[name]
        if not nets:
            continue
        w_units = int(width * 1000)
        circ = ('      (circuit' + NL + '        (use_layer ' + ' '.join(layers) + ')' + NL
                + '        (use_via "' + use_via + '")' + NL + '      )')
        rule = ('      (rule' + NL + '        (width ' + str(w_units) + ')' + NL
                + '        (clearance 150)' + NL + '      )')
        new_blocks += ('    (class ' + name + ' ' + ' '.join(nets) + NL
                       + circ + NL + rule + NL + '    )' + NL)
    text = text[:i] + new_blocks.rstrip() + NL + text[j + 1:]
    DSN.write_text(text, encoding='utf-8')
    counts = ', '.join(pp[0] + '=' + str(len(buckets[pp[0]])) for pp in LAYER_PLAN)
    print('DSN 层类已写入: ' + counts)

def run_freerouting(max_passes: int):
    cmd = [str(JAVA), "-jar", str(JAR), "-de", str(DSN), "-do", str(SES),
           "-mp", str(max_passes), "-mt", "1", "-l", "en"]
    print("Freerouting:", " ".join(cmd[1:]), flush=True)
    # 实时落盘, 避免黑箱等待
    with open(WS / "kicad" / "freerouting.log", "w", encoding="utf-8") as logf:
        p = subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT, cwd=str(FR_DIR))
        try:
            rc = p.wait(timeout=5400)
        except subprocess.TimeoutExpired:
            p.kill()
            print("!! Freerouting 超时(5400s)被终止")
            raise SystemExit(1)
    log = (WS / "kicad" / "freerouting.log").read_text(encoding="utf-8", errors="replace")
    if rc != 0:
        print(f"!! Freerouting 退出码 {rc}\n{log[-1500:]}")
        raise SystemExit(1)
    done = "100%" in log or "route completed" in log.lower()
    print(f"Freerouting 完成(exit {rc}, 100%布通标记={'有' if done else '无'})")
    for line in log.splitlines():
        if "Auto-routing stage completed" in line or "Fanout stage completed" in line:
            print("  ", line.split("INFO")[-1].strip()[:200])
    return SES.exists()


def run(cmd, **kw):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print("!! 命令失败:", " ".join(str(c) for c in cmd))
        print((r.stdout or "")[-800:], (r.stderr or "")[-800:])
        raise SystemExit(1)
    return r


def drc():
    run([KI / "kicad-cli.exe", "pcb", "drc", "--format", "json",
         "--schematic-parity", "--output", WS / "kicad" / "drc.json", PCB])
    rep = json.loads((WS / "kicad" / "drc.json").read_text(encoding="utf-8"))
    viol = rep.get("violations", [])
    unc = rep.get("unconnected_items", [])
    errs_v = [v for v in viol if v.get("severity") == "error"]
    errs_u = [v for v in unc if v.get("severity") == "error"]
    print(f"DRC: 违规 {len(viol)} (error {len(errs_v)}), 未连通 {len(unc)} (error {len(errs_u)})")
    for v in (errs_v + errs_u)[:15]:
        items = v.get("items", [])
        pos = items[0].get("pos") if items else {}
        print(f"   [{v.get('type')}] {v.get('description', '')[:90]} @ {pos}")
    return len(errs_v) + len(errs_u)


def fab_outputs():
    gdir = WS / "kicad" / "gerbers"
    gdir.mkdir(exist_ok=True)
    run([KI / "kicad-cli.exe", "pcb", "export", "gerbers", "--output", gdir, PCB])
    # KiCad 10 renamed --drill-format to the generic --format selector.
    run([KI / "kicad-cli.exe", "pcb", "export", "drill", "--output", gdir,
         "--format", "excellon", "--excellon-units", "mm", PCB])
    run([KI / "kicad-cli.exe", "pcb", "export", "pos", "--format", "csv", "--units", "mm",
         "--output", WS / "kicad" / "pos.csv", PCB])
    run([KI / "kicad-cli.exe", "sch", "export", "bom",
         "--output", WS / "kicad" / "bom.csv",
         "--fields", "Reference,Value,Footprint,${QUANTITY}",
         "--group-by", "Value,Footprint",
         WS / "kicad" / "stm32h743_core.kicad_sch"])
    print(f"制造文件: {gdir} (Gerber+钻孔), kicad/pos.csv, kicad/bom.csv")


if __name__ == "__main__":
    max_passes = 25
    if "--max-passes" in sys.argv:
        max_passes = int(sys.argv[sys.argv.index("--max-passes") + 1])
    step = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "all"
    if step in ("all", "dsn"):
        edit_dsn_power_class()
    if step in ("all", "route"):
        if not run_freerouting(max_passes):
            raise SystemExit("!! 未生成 SES")
    if step in ("all", "finish"):
        run([KI / "python.exe", WS / "tools" / "finish_pcb.py"])
    if step in ("all", "drc"):
        n = drc()
        raise SystemExit(0 if n == 0 else 2)
    if step in ("all", "fab"):
        fab_outputs()
