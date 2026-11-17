#!/usr/bin/env python3
"""C8 with mid-run resets (spec §5, §8 C6): as run.py, plus res_n pulled low at random cycles for 8-12
cycles (tb_resets.sv). Owner: Beru.

Rules checked at each reset (spec §5, #29/#30/#40):
- every cycle with res_n = 0, and reset cycles 1-7 after release: rw = 1, d_oe = 0;
- reset cycles 6-7 read FFFC, FFFD; cycle 8 (the 8th clock after the edge where res_n is first sampled 1)
  is the first fetch, and from there every pin is compared again (§4.0), with the model restarted at the
  vector: PC from FFFC/FFFD, I = 1, no pending NMI (§6 rule 6). The preamble rewrites A X Y S P (§5).
- memory: the model executes whole instructions, so at a reset it undoes the writes the RTL had not
  done. A write happens at the edge ending its write cycle, and only if res_n = 1 in that cycle (§5:
  writing is inhibited while res_n = 0). The model's RAM must then equal the RTL's, dumped right after
  the first res_n = 0 cycle (mem_rst<k>.hex), and at the end (mem_end.hex).
A program whose reset vector or preamble was overwritten before a reset stops being compared there
(counted), as does one reaching an undocumented byte.
Usage: tests/random/c8/run_resets.py [--nprog N] [--nst CYCLES] [--seed S] [--rtl DIR] [--rstdiv N]
"""
import argparse, os, random, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run
R, P = run.R, run.P
PRE_LEN = 15                                   # preamble bytes at run.PREAMBLE (see run.gen)


def read_dump(path):
    m = [int(l, 16) for l in open(path) if l.strip() and not l.startswith("//")]
    assert len(m) == 65536, f"{path}: {len(m)} bytes"
    return m


def compare(mem, lines, pdir):
    """Returns (err, stats). lines: per cycle [a rw sync d_oe d_out rdy irq_n nmi_n res_n]."""
    st = {"cycles": 0, "instructions": 0, "resets": 0, "undone": 0, "stopped": 0, "stopped_vector": 0}
    m = bytearray(mem)
    pending = []                               # (addr, old) of model writes not yet done on the bus

    def wr(a, v):
        pending.append((a, m[a])); m[a] = v
    c = R.CPU(m.__getitem__, wr)
    n = len(lines)
    rel = next((i for i, l in enumerate(lines) if l[8] == "1"), None)
    if rel is None:
        return "res_n never released", st
    nrst = 0
    while True:
        # reset cycles 1..7 after the release at `rel`, then cycle 8 = first fetch
        first = rel + 8
        if first >= n:
            return None, st
        for i in range(rel + 1, first):
            if lines[i][8] != "1":
                return f"cycle {i}: res_n low inside the reset sequence (testbench rule broken)", st
            if lines[i][1] != "1" or lines[i][3] != "0":
                return f"cycle {i} (reset cycle {i - rel}): rw={lines[i][1]} d_oe={lines[i][3]}, want 1 / 0", st
        if (int(lines[rel + 6][0], 16), int(lines[rel + 7][0], 16)) != (0xFFFC, 0xFFFD):
            return f"reset cycles 6-7 at {lines[rel + 6][0]} {lines[rel + 7][0]}, want fffc fffd", st
        c.pc = m[0xFFFC] | (m[0xFFFD] << 8); c.i = 1
        base = first
        inp = lambda k: (lambda j: int(lines[base + j][k]) if base + j < n else 1)
        pm = P.PinModel(c, rdy=inp(5), irq_n=inp(6), nmi_n=inp(7))
        g = pm.states()
        i = first
        while i < n and lines[i][8] == "1":
            try:
                w = next(g)
            except R.Undocumented:
                st["stopped"] = 1
                st["instructions"] += pm.instructions
                return None, st
            got = lines[i]
            want = ["%04x" % w.a, str(w.rw), str(w.sync), str(w.d_oe), "%02x" % w.d_out if w.d_oe else None]
            for k, name in enumerate(run.FIELDS):
                if want[k] is not None and got[k] != want[k]:
                    return (f"cycle {i} ({i - first} after the fetch at reset cycle 8): {name} rtl={got[k]} "
                            f"model={want[k]} | rtl {' '.join(got[:5])} | model {' '.join(x or '--' for x in want)}"), st
            if w.rw == 0:
                pending.pop(0)                 # this write cycle completed with res_n = 1
            st["cycles"] += 1
            i += 1
        st["instructions"] += pm.instructions
        if i >= n:
            break
        # reset: res_n = 0 in cycle i. Writes the model did that the RTL didn't: everything pending,
        # newest first (the write in cycle i itself, if any, is inhibited: §5).
        if lines[i][1] != "1" or lines[i][3] != "0":
            return f"cycle {i} (res_n = 0): rw={lines[i][1]} d_oe={lines[i][3]}, want 1 / 0", st
        for a, old in reversed(pending):
            m[a] = old; st["undone"] += 1
        pending.clear()
        dump = read_dump(f"{pdir}/mem_rst{nrst}.hex")
        diff = [a for a in range(65536) if m[a] != dump[a]]
        if diff:
            a = diff[0]
            return f"cycle {i}: RAM after RESET differs at {len(diff)} addresses, first {a:04X}: rtl {dump[a]:02X} model {m[a]:02X}", st
        nrst += 1; st["resets"] += 1
        if bytes(m[0xFFFC:0xFFFE]) != bytes(mem[0xFFFC:0xFFFE]) or bytes(m[run.PREAMBLE:run.PREAMBLE + PRE_LEN]) != bytes(mem[run.PREAMBLE:run.PREAMBLE + PRE_LEN]):
            st["stopped_vector"] = 1
            return None, st
        j = i
        while j < n and lines[j][8] == "0":
            if lines[j][1] != "1" or lines[j][3] != "0":
                return f"cycle {j} (res_n = 0): rw={lines[j][1]} d_oe={lines[j][3]}, want 1 / 0", st
            j += 1
        if j >= n:
            return None, st
        rel = j
    for a, old in reversed(pending):           # the run ended mid-instruction: those writes didn't happen
        m[a] = old
    end = read_dump(f"{pdir}/mem_end.hex")
    diff = [a for a in range(65536) if m[a] != end[a]]
    if diff:
        a = diff[0]
        return f"final RAM differs at {len(diff)} addresses, first {a:04X}: rtl {end[a]:02X} model {m[a]:02X}", st
    return None, st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nprog", type=int, default=20)
    ap.add_argument("--nst", type=int, default=12000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--rtl", default=os.path.join(run.ROOT, "rtl"))
    ap.add_argument("--out", default=os.path.join(run.ROOT, "build", "c8r"))
    ap.add_argument("--rstdiv", type=int, default=1500, help="a reset starts in 1 of N running cycles")
    a = ap.parse_args()
    progs = []
    for p in range(a.nprog):
        mem = run.gen(random.Random(a.seed * 100003 + p))
        d = f"{a.out}/prog{p}"
        os.makedirs(d, exist_ok=True)
        for f in os.listdir(d):
            os.remove(os.path.join(d, f))
        open(f"{d}/mem.hex", "w").write("\n".join("%02x" % v for v in mem) + "\n")
        progs.append(mem)
    rtl = sorted(os.path.join(dp, f) for dp, _, fs in os.walk(a.rtl) for f in fs if f.endswith(".v"))
    vvp = f"{a.out}/c8r.vvp"
    subprocess.run(["iverilog", "-g2012", "-o", vvp, *rtl, os.path.join(HERE, "tb_resets.sv")], check=True)
    sim = subprocess.run(["vvp", "-n", vvp, f"+dir={a.out}", f"+nprog={a.nprog}", f"+nst={a.nst}", f"+seed={a.seed}",
                          f"+rstdiv={a.rstdiv}"], capture_output=True, text=True)
    if "DONE c8 resets tb" not in sim.stdout:
        print(sim.stdout[-2000:], sim.stderr[-2000:]); print("FAIL: simulator problems"); return 1
    bad = 0
    tot = {"cycles": 0, "instructions": 0, "resets": 0, "undone": 0, "stopped": 0, "stopped_vector": 0}
    for p, mem in enumerate(progs):
        lines = [l.split() for l in open(f"{a.out}/prog{p}/pins.txt")]
        err, st = compare(mem, lines, f"{a.out}/prog{p}")
        for k in tot: tot[k] += st[k]
        if err:
            bad += 1
            if bad <= 10:
                print(f"MISMATCH prog{p} (seed {a.seed}, program {p}): {err}")
    print(f"compared: {tot['cycles']} cycles, {tot['instructions']} instructions, resets {tot['resets']}, "
          f"model writes undone at a reset: {tot['undone']}")
    print(f"stopped early: {tot['stopped']} at an undocumented byte, {tot['stopped_vector']} with the reset vector or "
          f"preamble overwritten before a reset")
    print(f"c8 resets: seed={a.seed} programs={a.nprog} cycles={a.nst} mismatching_programs={bad}")
    print("PASS" if bad == 0 else "FAIL")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
