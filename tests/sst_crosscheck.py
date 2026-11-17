#!/usr/bin/env python3
"""Cross-check of tests/mach6502.py against SingleStepTests/65x02 (spec 9 item 2: a cross-check, not ground truth; MIT licence; fetched to a scratch directory, never
committed). For each opcode file <dir>/<xx>.json (10,000 tests with initial/final state and one [address, value, "read"|"write"] per cycle), runs the model from
`initial` and compares the cycles and the final registers, P and RAM. Usage: sst_crosscheck.py <dir> [tests-per-opcode] [opcode ...]
Differences are listed per opcode; where a vector disagrees with a rule taken from a MOS manual, the spec wins (it is filed as an issue)."""
import json, os, sys
sys.dont_write_bytecode = True
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import asm6502 as A, mach6502 as M
d = sys.argv[1]; limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10000
ops = sys.argv[3:] or ["%02x" % v for v in sorted(A.OPS.values())]
tot = bad_ops = 0
for op in ops:
    tests = json.load(open(os.path.join(d, op + ".json")))[:limit]; nbad = 0; first = None
    for t in tests:
        i, f = t["initial"], t["final"]; m = M.Mach(i["pc"]); m.a, m.x, m.y, m.s = i["a"], i["x"], i["y"], i["s"]; m.setp(i["p"]); m.mem = {a: v for a, v in i["ram"]}
        cyc = m.step(); got = [[a, v, "read" if rw else "write"] for a, rw, v, sy in cyc]
        gp = m.p(0) & 0xCF | (i["p"] & 0x10) if False else m.p(0)
        fin = {a: v for a, v in f["ram"]}
        ok = got == t["cycles"] and (m.pc, m.s, m.a, m.x, m.y) == (f["pc"], f["s"], f["a"], f["x"], f["y"]) and (m.p(0) & 0xCF) == (f["p"] & 0xCF) and all(m.mem.get(a, 0) == v for a, v in fin.items())
        if not ok:
            nbad += 1
            if first is None: first = (t["name"], got, t["cycles"], (m.pc, m.s, m.a, m.x, m.y, m.p(0)), f)
    tot += len(tests)
    if nbad:
        bad_ops += 1; print(f"opcode {op}: {nbad}/{len(tests)} differ; first {first[0]}: model cycles {first[1]} / vector {first[2]}; model state {first[3]} / vector final {first[4]['pc'], first[4]['s'], first[4]['a'], first[4]['x'], first[4]['y'], first[4]['p']}")
print(f"{'PASS' if not bad_ops else 'FAIL'} sst_crosscheck: {len(ops)} opcodes, {tot} tests, {bad_ops} opcodes with differences")
sys.exit(1 if bad_ops else 0)
