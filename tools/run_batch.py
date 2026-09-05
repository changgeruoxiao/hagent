#!/usr/bin/env python3
"""实验批次运行器(须用 KiCad python): 同一 fresh DSN 跑 3 次独立 Freerouting,
每次独立导入/灌铜/DRC, 采集 min/median/max 指标并落盘 build_status.json。

用法: <KiCad>/bin/python.exe tools/run_batch.py [runs=3] [passes=8]
"""
import json
import re
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
from project_config import DSN, PCB, WS as _WS  # noqa: E402

FR_DIR = WS / "tools" / "freerouting"
JAVA = sorted(FR_DIR.glob("jdk-*/bin/java.exe"))[-1]
JAR = FR_DIR / "freerouting.jar"
KPY = Path(r"C:\Users\27417\AppData\Local\Programs\KiCad\10.0\bin\python.exe")
KI = Path(r"C:\Users\27417\AppData\Local\Programs\KiCad\10.0\bin\kicad-cli.exe")
LOGDIR = WS / "kicad" / "batch"
PCB = WS / "kicad" / "stm32h743_core.kicad_pcb"

RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 3
PASSES = int(sys.argv[2]) if len(sys.argv) > 2 else 8


def out(*a):
    print(*a, flush=True)


def sh(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)


def main():
    LOGDIR.mkdir(exist_ok=True)
    # 基线: fresh 板 + 层类 DSN (各 run 共用同一份 DSN)
    sh([KPY, WS / "tools" / "gen_pcb.py"], cwd=str(WS))
    sh([sys.executable, WS / "tools" / "pipeline_pcb.py", "dsn"], cwd=str(WS))
    pristine = PCB.read_bytes()
    results = []

    for i in range(1, RUNS + 1):
        ses_i = WS / "kicad" / f"ses_run{i}.ses"
        log_i = WS / "kicad" / f"freerouting_run{i}.log"
        out(f"--- Freerouting run {i}/{RUNS} ---")
        t0 = time.time()
        ses_done = ses_i.exists() and log_i.exists() and "final score" in log_i.read_text(
            encoding="utf-8", errors="replace")
        if ses_done:
            rc = 0
            runtime = -1.0
            out("  已有 SES, 跳过布线(断点续跑)")
        if not ses_done:
            with open(log_i, "w", encoding="utf-8") as lf:
                proc = subprocess.Popen(
                    [str(JAVA), "-jar", str(JAR), "-de", str(DSN), "-do", str(ses_i),
                     "-mp", str(PASSES), "-mt", "1", "-l", "en"],
                    stdout=lf, stderr=subprocess.STDOUT, cwd=str(FR_DIR))
                rc = proc.wait(timeout=5400)
            runtime = time.time() - t0
        log = log_i.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"final score: [\d.]+ \((\d+) unrouted and (\d+) violations\)", log)
        unr = int(m.group(1)) if m else -1
        vio = int(m.group(2)) if m else -1
        vias = len(re.findall(r"\(marker (?:via|padstack)", log))
        results.append({"run": i, "rc": rc, "runtime_s": round(runtime, 1),
                        "unrouted": unr, "violations": vio, "ses": str(ses_i), "log": str(log_i)})
        out(f"  run{i}: exit={rc} unrouted={unr} violations={vio} {runtime:.0f}s")
        if rc != 0 or not ses_i.exists():
            out("!! 该 run 失败, 中止批次")
            raise SystemExit(1)

        # 导入该 run 的 SES 到 fresh 板并出 DRC JSON(供事后统计)
        PCB.write_bytes(pristine)
        sh([KPY, WS / "tools" / "finish_pcb.py"], cwd=str(WS))
        shutil.copy2(PCB, WS / "kicad" / f"board_run{i}.kicad_pcb")
        sh([KI, "pcb", "drc", "--format", "json",
            "--output", WS / "kicad" / f"drc_run{i}.json", PCB])
        rep = json.loads((WS / "kicad" / f"drc_run{i}.json").read_text(encoding="utf-8"))
        e = sum(1 for x in rep.get("violations", []) if x.get("severity") == "error")
        u = sum(1 for x in rep.get("unconnected_items", []) if x.get("severity") == "error")
        results[-1].update(drc_errors=e, drc_unconnected=u)
        out(f"  run{i} DRC: error={e} unconnected={u}")

    # 汇总
    ok = [r for r in results if r.get("drc_unconnected") is not None]
    summary = {
        "runs": results,
        "unconnected": [r.get("drc_unconnected") for r in results],
        "drc_errors": [r.get("drc_errors") for r in results],
        "runtime_s": [r["runtime_s"] for r in results],
    }
    (WS / "kicad" / "batch_results.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    out("=== 批次汇总 ===")
    for key in ("unconnected", "drc_errors"):
        vals = sorted(summary[key])
        out(f"  {key}: {vals} (min={vals[0]}, median={vals[len(vals)//2]}, max={vals[-1]})")
    best = min(results, key=lambda r: (r.get("drc_unconnected", 999), r.get("drc_errors", 999)))
    out(f"最优 run: #{best['run']} (unrouted={best.get('unrouted')}, drc_unc={best.get('drc_unconnected')})")


if __name__ == "__main__":
    main()
