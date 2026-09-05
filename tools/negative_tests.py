#!/usr/bin/env python3
"""门禁负测试(mutation tests): 原地突变正式产物 → 验证门禁拦截 → 恢复。

每个用例: 备份产物 → 原地注入已知坏例 → 运行门禁(期望非零) → try/finally 恢复。
用法: <KiCad>/bin/python.exe tools/negative_tests.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
from project_config import DRC, NET, PCB, SCH  # noqa: E402

KPY = Path(r"C:\Users\27417\AppData\Local\Programs\KiCad\10.0\bin\python.exe")
RESULTS = []


def run_gate(script: str) -> int:
    r = subprocess.run([str(KPY), str(WS / "tools" / script)],
                       capture_output=True, text=True, cwd=str(WS))
    return r.returncode


def case(name: str, gate: str, mutate, files: tuple):
    backups = {f: f.read_bytes() for f in files if f.exists()}
    rc = 0
    try:
        mutate()
        rc = run_gate(gate)
    finally:
        for f, data in backups.items():
            f.write_bytes(data)
    blocked = rc != 0
    RESULTS.append((name, gate, rc, "✓拦截" if blocked else "✗未按预期"))


def m_ss_rename():
    t = NET.read_text(encoding="utf-8")
    NET.write_text(t.replace('(name "/SS")', '(name "/SS_DELETED")', 1), encoding="utf-8")


def m_u24_drop():
    t = NET.read_text(encoding="utf-8")
    NET.write_text(re.sub(r'\(node\s+\(ref "U2"\)\s*\(pin "4"\)[^)]*\)', "", t, count=1),
                   encoding="utf-8")


def m_pd13_in1():
    t = PCB.read_text(encoding="utf-8")
    PCB.write_text(t.replace('(layer "In2.Cu")', '(layer "In1.Cu")', 1), encoding="utf-8")


def m_footprint_missing():
    t = PCB.read_text(encoding="utf-8")
    t = re.sub(r'\(footprint "C28".*?\n\t\)\n', "\n", t, count=1, flags=re.S)
    PCB.write_text(t, encoding="utf-8")


def m_net_stale():
    import os
    old = NET.stat().st_mtime_ns - 10**11
    os.utime(NET, ns=(old, old))


def main() -> int:
    if not NET.exists() or not PCB.exists():
        print("缺少产物, 先跑一次全链")
        return 1
    case("负测试1: SS 网名破坏 → netlist 拦截", "check_netlist.py", m_ss_rename, (NET,))
    case("负测试2: U2.4 节点删除 → netlist 拦截", "check_netlist.py", m_u24_drop, (NET,))
    case("负测试3: PD13 走 In1 → layer policy 拦截", "check_layer_policy.py", m_pd13_in1, (PCB,))
    case("负测试4: PCB 缺 C28 封装 → parity 拦截", "check_schematic_parity.py", m_footprint_missing, (PCB,))
    case("负测试5: .net 早于 .sch → release gate lineage 拦截", "release_gate.py", m_net_stale, (NET,))

    print("\n=== 负测试结果 ===")
    bad = 0
    for name, gate, rc, verdict in RESULTS:
        print(f"  {verdict}  {name} (exit={rc})")
        if "✗" in verdict:
            bad += 1
    print(f"\n{'✓ 全部负测试符合预期' if bad == 0 else f'✗ {bad} 项未按预期'}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
