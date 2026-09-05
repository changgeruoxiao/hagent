#!/usr/bin/env python3
"""PCB 流水线编排(系统 python): DSN 分类 -> Freerouting -> SES 回写 -> DRC -> Release Gate -> 制造文件。

用法: python tools/pipeline_pcb.py [--max-passes 25]
"""
import json
import subprocess
import sys
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
FR_DIR = WS / "tools" / "freerouting"
JAVA = FR_DIR / "jdk-25.0.4.1+1-jre" / "bin" / "java.exe"
JAR = FR_DIR / "freerouting.jar"

sys.path.insert(0, str(WS / "tools"))
from project_config import (  # noqa: E402
    CLEARANCE,
    DSN,
    GND_TRACE_WIDTH,
    IN2_ALLOWED_SIGNAL_NETS,
    KI,
    PCB,
    POWER_WIDTH,
    SES,
    SIGNAL_LAYERS,
    SIGNAL_WIDTH,
)

# Current experiment-B routing classes.
# In1 remains GND-only. In2 may carry +3V3 plus explicit ordinary GPIO names.
LAYER_PLAN = [
    ("GND", ["GND"], GND_TRACE_WIDTH, ["In1.Cu", *SIGNAL_LAYERS]),
    ("P3V3", ["+3V3"], POWER_WIDTH, ["In2.Cu", *SIGNAL_LAYERS]),
    ("POW5", ["+5V", "VBUS", "VBUS_F", "5VIN", "PH", "3V3_SW", "BOOT"], POWER_WIDTH, list(SIGNAL_LAYERS)),
    ("SIG2", None, SIGNAL_WIDTH, ["F.Cu", "In2.Cu", "B.Cu"]),
    ("Default", None, SIGNAL_WIDTH, list(SIGNAL_LAYERS)),
]
POWER_NETS = LAYER_PLAN[1][1] + LAYER_PLAN[2][1]
NL = chr(10)


def edit_dsn_power_class():
    """按 LAYER_PLAN 把网络分入带 use_layer 约束的类。"""
    text = DSN.read_text(encoding="utf-8")
    # DSN 每次应由 gen_pcb 新导出；若发现已分类，拒绝静默复用旧实验配置。
    if "(class GND " in text or "(class SIG2 " in text:
        raise SystemExit("!! DSN 已包含自定义层类；请从当前 PCB 重新导出 DSN 后再执行 dsn 步骤")
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
            buckets["SIG2" if tok in IN2_ALLOWED_SIGNAL_NETS else "Default"].append(tok)

    new_blocks = ""
    for name, members, width, layers in LAYER_PLAN:
        nets = buckets[name]
        if not nets:
            continue
        w_units = int(width * 1000)
        clearance_units = int(CLEARANCE * 1000)
        circ = (
            "      (circuit" + NL
            + "        (use_layer " + " ".join(layers) + ")" + NL
            + "        (use_via \"" + use_via + "\")" + NL
            + "      )"
        )
        rule = (
            "      (rule" + NL
            + "        (width " + str(w_units) + ")" + NL
            + "        (clearance " + str(clearance_units) + ")" + NL
            + "      )"
        )
        new_blocks += (
            "    (class " + name + " " + " ".join(nets) + NL
            + circ + NL + rule + NL + "    )" + NL
        )
    text = text[:i] + new_blocks.rstrip() + NL + text[j + 1:]
    DSN.write_text(text, encoding="utf-8")
    counts = ", ".join(pp[0] + "=" + str(len(buckets[pp[0]])) for pp in LAYER_PLAN)
    print("DSN 层类已写入: " + counts)


def run_freerouting(max_passes: int):
    cmd = [str(JAVA), "-jar", str(JAR), "-de", str(DSN), "-do", str(SES),
           "-mp", str(max_passes), "-mt", "1", "-l", "en"]
    print("Freerouting:", " ".join(cmd[1:]), flush=True)
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
        raise SystemExit(r.returncode or 1)
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


def release_gate():
    run([sys.executable, WS / "tools" / "release_gate.py"], cwd=str(WS))


def fab_outputs():
    # Fail closed: manufacturing export is not allowed without the full gate.
    release_gate()
    gdir = WS / "kicad" / "gerbers"
    gdir.mkdir(exist_ok=True)
    run([KI / "kicad-cli.exe", "pcb", "export", "gerbers", "--output", gdir, PCB])
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
        if n:
            raise SystemExit(2)
    if step in ("all", "gate"):
        release_gate()
    if step in ("all", "fab"):
        fab_outputs()
