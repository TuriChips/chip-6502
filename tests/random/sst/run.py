#!/usr/bin/env python3
"""Cross-check of ref/ref6502.py against SingleStepTests 65x02 (spec §9 item 2). Owner: Beru.

SingleStepTests (github.com/SingleStepTests/65x02, MIT) are emulator-generated, not hardware-verified, so
they're a cross-check, not ground truth: where a vector disagrees with a spec rule taken from a MOS
manual, the spec wins and the case goes to Igris as an issue. The vectors are fetched at test time,
pinned by commit, into build/sst/ (never committed, rule 9). Only the 151 documented opcodes' files (§6.0).

Per test: initial registers and RAM → one ref6502 step → compare every bus cycle (address, data,
read/write), final registers (P with B and bit 5 masked: they aren't stored bits, §3), and final RAM.
A read of an address the vector doesn't list is an error ("any address not listed must not be
accessed"); writes are checked through final RAM. Usage: tests/random/sst/run.py [--ops a9,7d,...] [--n PER_FILE]
"""
import argparse, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "ref"))
import ref6502 as R

COMMIT = "2f6980a2d95757486c7bee24355c360e40e2a224"
URL = f"https://raw.githubusercontent.com/SingleStepTests/65x02/{COMMIT}/6502/v1/{{}}.json"


def fetch(op, cache):
    path = f"{cache}/{op:02x}.json"
    if not os.path.exists(path):
        os.makedirs(cache, exist_ok=True)
        subprocess.run(["curl", "-sfL", "-o", path + ".part", URL.format(f"{op:02x}")], check=True)
        os.replace(path + ".part", path)
    return path


def run_test(t):
    ini, fin = t["initial"], t["final"]
    mem = {a: v for a, v in ini["ram"]}
    stray = []

    def rd(a):
        if a not in mem:
            stray.append(a); return 0
        return mem[a]

    def wr(a, v):                       # writes may go anywhere; final RAM lists them
        mem[a] = v
    c = R.CPU(rd, wr)
    c.pc, c.s, c.a, c.x, c.y = ini["pc"], ini["s"], ini["a"], ini["x"], ini["y"]
    c.set_p(ini["p"])
    cyc = c.step()
    got = [[a, d, "read" if rw else "write"] for a, rw, d, _ in cyc]
    if got != t["cycles"]:
        k = next((i for i in range(max(len(got), len(t["cycles"])))
                  if i >= len(got) or i >= len(t["cycles"]) or got[i] != t["cycles"][i]), None)
        return f"cycle {k}: model {got[k] if k < len(got) else '-'} vector {t['cycles'][k] if k < len(t['cycles']) else '-'} ({len(got)} vs {len(t['cycles'])} cycles)"
    regs = {"pc": c.pc, "s": c.s, "a": c.a, "x": c.x, "y": c.y, "p": c.p_byte(0) & 0xCF}
    for k, v in regs.items():
        want = fin[k] & 0xCF if k == "p" else fin[k]
        if v != want:
            return f"{k}: model {v:02X} vector {want:02X}"
    for a, v in fin["ram"]:
        if mem.get(a) != v:
            return f"ram {a:04X}: model {mem.get(a)} vector {v}"
    if stray:
        return f"read unlisted addresses {[hex(x) for x in stray[:4]]}"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ops", default=None, help="comma-separated hex opcodes (default: all 151 documented)")
    ap.add_argument("--n", type=int, default=10000, help="tests per file")
    ap.add_argument("--cache", default=os.path.join(ROOT, "build", "sst"))
    a = ap.parse_args()
    ops = sorted(int(x, 16) for x in a.ops.split(",")) if a.ops else sorted(R.OPS)
    assert not set(ops) & R.UNDOCUMENTED, "only the 151 documented opcodes (§6.0)"
    total = bad = 0
    per_op = {}
    for op in ops:
        tests = json.load(open(fetch(op, a.cache)))[: a.n]
        nbad = 0
        for t in tests:
            total += 1
            err = run_test(t)
            if err:
                nbad += 1
                if nbad <= 3:
                    print(f"DIFF {op:02X} {R.OPS[op][0]} {R.OPS[op][1]} [{t['name']}] {err}")
        per_op[op] = (len(tests), nbad)
        bad += nbad
    for op, (n, nb) in per_op.items():
        if nb:
            print(f"  {op:02X} {R.OPS[op][0]:3} {R.OPS[op][1]:3}: {nb}/{n} differ")
    print(f"sst: commit {COMMIT[:10]} opcodes={len(ops)} tests={total} differing={bad}")
    print("PASS" if bad == 0 else "FAIL")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
