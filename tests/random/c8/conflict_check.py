#!/usr/bin/env python3
"""Positive bus_conflict check (spec §8 C7, "the positive-case test", 8080 lesson). Owner: Beru.

Builds a copy of the RTL with one deliberate fault: the CPU also drives the data bus (d_oe = 1) in every
opcode fetch, a read cycle in which memory drives. Runs a C8 program on m6502_system (tb_conflict.sv)
and checks that bus_conflict = 1 in at least one cycle, and only in cycles where d_oe = 1 and rw = 1.
Then runs the same program on the unmodified RTL and checks bus_conflict is never 1.
The mutant is built under build/, never committed. Usage: tests/random/c8/conflict_check.py [--rtl DIR]
"""
import argparse, os, random, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
import run

FAULT_FROM = ".d_oe(d_oe)"
FAULT_TO = ".d_oe(d_oe_ctl)"
FAULT_WIRE = "    wire d_oe_ctl;\n    assign d_oe = d_oe_ctl | sync;   // FAULT (conflict_check): CPU drives in opcode fetches\nendmodule"


def sim(rtl, out, mem):
    os.makedirs(out, exist_ok=True)
    open(f"{out}/mem.hex", "w").write("\n".join("%02x" % v for v in mem) + "\n")
    srcs = sorted(os.path.join(dp, f) for dp, _, fs in os.walk(rtl) for f in fs if f.endswith(".v"))
    subprocess.run(["iverilog", "-g2012", "-o", f"{out}/c.vvp", *srcs, os.path.join(HERE, "tb_conflict.sv")], check=True)
    r = subprocess.run(["vvp", "-n", f"{out}/c.vvp", f"+dir={out}", "+nst=2000"], capture_output=True, text=True)
    assert "DONE conflict tb" in r.stdout, r.stdout[-1000:]
    rows = [l.split() for l in open(f"{out}/conflict.txt")]
    conf = [r for r in rows if r[3] == "1"]
    return len(conf), sum(1 for r in conf if r[1] == "1" and r[2] == "1")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rtl", default=os.path.join(ROOT, "rtl"))
    a = ap.parse_args()
    work = os.path.join(ROOT, "build", "conflict_check")
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(a.rtl, f"{work}/rtl")
    top = f"{work}/rtl/top.v"
    src = open(top).read()
    if FAULT_FROM not in src or src.count("endmodule") != 1:
        print("FAIL conflict_check: rtl/top.v's d_oe connection changed; update FAULT_FROM"); return 1
    src = src.replace(FAULT_FROM, FAULT_TO, 1)
    src = src[:src.rindex("endmodule")] + FAULT_WIRE + src[src.rindex("endmodule") + len("endmodule"):]
    open(top, "w").write(src)
    mem = run.gen(random.Random(7))
    conf_m, both_m = sim(f"{work}/rtl", f"{work}/fault", mem)
    conf_ok, _ = sim(a.rtl, f"{work}/clean", mem)
    print(f"faulty RTL: bus_conflict = 1 in {conf_m} cycles, {both_m} of them with d_oe = rw = 1")
    print(f"clean RTL:  bus_conflict = 1 in {conf_ok} cycles")
    ok = conf_m > 0 and both_m == conf_m and conf_ok == 0
    print(("PASS" if ok else "FAIL") + " conflict_check: bus_conflict rises exactly when two drivers are on")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
