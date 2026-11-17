#!/usr/bin/env python3
"""C8 (spec §8): random programs on the RTL vs ref/pins6502.py, every pin every cycle. Owner: Beru.

Per program: a random image (generator below), the testbench (tb.sv) runs it with random RDY / IRQ / NMI
and dumps each cycle's pins and inputs; the model replays those inputs and must match on every cycle:
a, rw, sync, d_oe always, d_out when d_oe = 1 (spec §4.0). Before that, the reset rules (§5): rw = 1 and
d_oe = 0 from res_n = 0 until the first sync, the first fetch in reset cycle 8 (sync compared from there),
the vector reads at FFFC/FFFD in reset cycles 6-7. Comparison never pauses after cycle 8 (§4.0, §5).
A program whose execution reaches one of the 105 undocumented bytes (§6: not tested) stops being
compared there and is counted as "stopped".

Generator: memory outside the stream is 70% harmless 1-byte opcodes (SAFE) and 30% any documented opcode,
so wild control flow keeps running documented code. A preamble at the reset vector writes S, A, X, Y, D, C, V, N, Z (I is 1 after reset, §3)
before anything reads them, then jumps to a 4 KiB stream of random documented instructions at 0200.
Jump, JSR and branch targets are instruction starts; JMP (ind) pointers (some at $xxFF) are in the data
area; zero page holds pointers into the data area for (zp,X) and (zp),Y; BRK is followed by a pad byte.
IRQ/BRK and NMI handlers are a few random instructions and RTI.
Usage: tests/random/c8/run.py [--nprog N] [--nst CYCLES] [--seed S] [--rtl DIR] [--out DIR]
                              [--rdy PCT] [--irq PERMILLE] [--nmi PERMILLE]
"""
import argparse, os, random, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "ref"))
import ref6502 as R, pins6502 as P

CODE, CODE_END = 0x0200, 0x1200
DATA, DATA_END = 0x1200, 0xEF00
PREAMBLE, IRQ_H, NMI_H = 0xF800, 0xF900, 0xFA00
RESET_CYCLES = 10
SIMPLE = [op for op, (m, md) in R.OPS.items() if m in R.READ_OPS | R.RMW_OPS | {"STA", "STX", "STY", "CLC", "SEC",
          "CLV", "TAX", "TAY", "TXA", "TYA", "INX", "INY", "DEX", "DEY", "NOP", "CLD", "SED"}]
RARE = {"RTI": 1, "RTS": 2, "PLA": 3, "PLP": 2, "BRK": 2, "TXS": 2, "JSR": 4, "JMP": 4}


def operand(rng, op, mode, starts_hint):
    m = R.OPS[op][0]
    if mode in ("imm",):
        return [rng.randrange(256)]
    if mode in ("zp", "zpx", "zpy", "izx", "izy"):
        return [rng.choice([rng.randrange(256), 0xFF, 0x00, rng.randrange(0x40)])]
    if mode in ("abs", "abx", "aby"):
        if m in ("JMP", "JSR"):
            return None                                   # patched to an instruction start
        r = rng.random()
        a = (rng.randrange(DATA, DATA_END) if r < 0.85 else rng.randrange(0x0000, 0x0200) if r < 0.95
             else rng.choice([0x10FF, 0x20FF, 0x80F0]))
        return [a & 0xFF, a >> 8]
    if mode == "ind":
        return None
    if mode == "rel":
        return None
    return []


# 1-byte documented opcodes with no control flow and no stack use: a wild jump (an RTS/RTI pulling a
# non-code address, a self-modified operand) that lands on them keeps executing documented code and
# slides forward into the preamble at F800, which re-initialises and jumps back to the stream.
SAFE = [op for op, (m, md) in R.OPS.items() if md in ("imp", "acc") and m not in
        ("BRK", "RTI", "RTS", "PHA", "PLA", "PHP", "PLP", "TXS")]
SAFE_FILL = 0.7                       # share of non-code bytes taken from SAFE; the rest any documented opcode
DOC = sorted(R.OPS)                   # (stores write all 256 values as programs run, so data still varies)


def gen(rng):
    mem = bytearray(rng.choice(SAFE) if rng.random() < SAFE_FILL else rng.choice(DOC) for _ in range(65536))
    for zp in range(0, 256, 2):                           # zero-page pointers into the data area
        if rng.random() < 0.8:
            a = rng.randrange(DATA, DATA_END - 0x200)
            mem[zp], mem[zp + 1] = a & 0xFF, a >> 8
    ops = list(R.OPS)
    weights = [RARE.get(R.OPS[o][0], 10) for o in ops]
    # stream
    pc, starts, fix = CODE, [], []
    while pc < CODE_END - 8:
        op = rng.choices(ops, weights)[0]
        m, mode = R.OPS[op]
        starts.append(pc)
        mem[pc] = op
        if m == "BRK":
            mem[pc + 1] = rng.randrange(256); pc += 2; continue
        opnd = operand(rng, op, mode, starts)
        length = {"imp": 1, "acc": 1, "rel": 2, "ind": 3}.get(mode, None)
        if opnd is None:
            fix.append((pc, op)); pc += length or 3; continue
        mem[pc + 1:pc + 1 + len(opnd)] = bytes(opnd)
        pc += 1 + len(opnd)
    mem[pc:pc + 3] = bytes([0x4C, CODE & 0xFF, CODE >> 8])        # JMP back to the start
    starts.append(pc)
    for at, op in fix:
        m, mode = R.OPS[op]
        if mode == "rel":
            near = [s for s in starts if -128 <= s - (at + 2) <= 127]
            t = rng.choice(near) if near else at + 2
            mem[at + 1] = (t - (at + 2)) & 0xFF
        elif mode == "ind":
            t = rng.choice(starts)
            ptr = rng.choice([rng.randrange(DATA, DATA_END), (rng.randrange(DATA >> 8, DATA_END >> 8) << 8) | 0xFF])
            mem[ptr] = t & 0xFF
            mem[(ptr & 0xFF00) | ((ptr + 1) & 0xFF)] = t >> 8                 # §6: high byte from $xx00 on a wrap
            mem[at + 1], mem[at + 2] = ptr & 0xFF, ptr >> 8
        else:
            t = rng.choice(starts)
            mem[at + 1], mem[at + 2] = t & 0xFF, t >> 8
    # preamble: write everything before reading anything (§5)
    pre = [0xD8 if rng.random() < 0.7 else 0xF8, 0xB8, 0x18 if rng.random() < 0.5 else 0x38,
           0xA2, rng.randrange(256), 0x9A,                                    # LDX #s; TXS
           0xA9, rng.randrange(256), 0xA0, rng.randrange(256), 0xA2, rng.randrange(256),
           0x4C, CODE & 0xFF, CODE >> 8]
    mem[PREAMBLE:PREAMBLE + len(pre)] = bytes(pre)
    for h in (IRQ_H, NMI_H):
        pc = h
        for _ in range(rng.randrange(4)):
            op = rng.choice([o for o in SIMPLE if R.OPS[o][1] in ("imp", "acc", "imm", "zp")])
            mem[pc] = op
            n = 1 if R.OPS[op][1] in ("imp", "acc") else 2
            if n == 2: mem[pc + 1] = rng.randrange(256)
            pc += n
        mem[pc] = 0x40                                                        # RTI
    mem[0xFFFA], mem[0xFFFB] = NMI_H & 0xFF, NMI_H >> 8
    mem[0xFFFC], mem[0xFFFD] = PREAMBLE & 0xFF, PREAMBLE >> 8
    mem[0xFFFE], mem[0xFFFF] = IRQ_H & 0xFF, IRQ_H >> 8
    return mem


FIELDS = "a rw sync d_oe d_out".split()


def compare(mem, lines):
    """lines: per cycle [a rw sync d_oe d_out rdy irq_n nmi_n res_n] (strings). Returns (err, stats)."""
    st = {"cycles": 0, "instructions": 0, "IRQ": 0, "NMI": 0, "stopped": 0, "rdy_holds": 0}
    rel = next((i for i, l in enumerate(lines) if l[8] == "1"), None)
    if rel is None:
        return "res_n never released", st
    # §5 (#29): res_n is first sampled 1 at the edge ending cycle `rel`, so reset cycle 1 is rel + 1 and
    # the first fetch, cycle 8, is rel + 8. sync isn't compared before cycle 8; rw = 1 and d_oe = 0 are.
    first = rel + 8
    if first >= len(lines):
        return "run too short for the reset sequence", st
    for i in range(first):
        if lines[i][1] != "1" or lines[i][3] != "0":
            return f"cycle {i} (reset): rw={lines[i][1]} d_oe={lines[i][3]}, want 1 / 0", st
    sa = [int(lines[rel + k][0], 16) for k in (3, 4, 5)]
    s0 = sa[0] & 0xFF
    if sa != [0x100 | s0, 0x100 | ((s0 - 1) & 0xFF), 0x100 | ((s0 - 2) & 0xFF)]:
        st["reset_stack"] = " ".join("%04x" % x for x in sa)
    if (int(lines[rel + 6][0], 16), int(lines[rel + 7][0], 16)) != (0xFFFC, 0xFFFD):
        return f"reset cycles 6-7 at {lines[rel + 6][0]} {lines[rel + 7][0]}, want fffc fffd", st
    m = bytearray(mem)
    c = R.CPU(m.__getitem__, m.__setitem__)
    c.pc = mem[0xFFFC] | (mem[0xFFFD] << 8); c.i = 1
    inp = lambda k: (lambda n: int(lines[first + n][k]) if first + n < len(lines) else 1)
    pm = P.PinModel(c, rdy=inp(5), irq_n=inp(6), nmi_n=inp(7))
    g = pm.states()
    for i in range(first, len(lines)):
        try:
            w = next(g)
        except R.Undocumented:
            st["stopped"] = 1
            break
        got = lines[i]
        want = ["%04x" % w.a, str(w.rw), str(w.sync), str(w.d_oe), "%02x" % w.d_out if w.d_oe else None]
        for k, name in enumerate(FIELDS):
            if want[k] is not None and got[k] != want[k]:
                return (f"cycle {i - first} after the first fetch: {name} rtl={got[k]} model={want[k]} | rtl "
                        f"{' '.join(got[:5])} | model {' '.join(x or '--' for x in want)} | inputs rdy/irq/nmi "
                        f"{' '.join(got[5:8])}"), st
        st["cycles"] += 1
        st["rdy_holds"] += got[5] == "0" and w.rw == 1
    st["instructions"], st["IRQ"], st["NMI"] = pm.instructions, pm.interrupts["IRQ"], pm.interrupts["NMI"]
    return None, st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nprog", type=int, default=20)
    ap.add_argument("--nst", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--rtl", default=os.path.join(ROOT, "rtl"))
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "c8"))
    ap.add_argument("--rdy", type=int, default=10)
    ap.add_argument("--irq", type=int, default=30)
    ap.add_argument("--nmi", type=int, default=10)
    ap.add_argument("--timeout", type=float, default=None, help="seconds; a simulation still running then is a FAIL")
    ap.add_argument("--extra", nargs="*", default=[], help="extra Verilog files (gate level: PDK cell models)")
    ap.add_argument("--define", nargs="*", default=[], help="iverilog -D macros")
    a = ap.parse_args()
    progs = []
    for p in range(a.nprog):
        mem = gen(random.Random(a.seed * 100003 + p))
        d = f"{a.out}/prog{p}"
        os.makedirs(d, exist_ok=True)
        open(f"{d}/mem.hex", "w").write("\n".join("%02x" % v for v in mem) + "\n")
        progs.append(mem)
    rtl = sorted(os.path.join(dp, f) for dp, _, fs in os.walk(a.rtl) for f in fs if f.endswith(".v"))
    vvp = f"{a.out}/c8.vvp"
    subprocess.run(["iverilog", "-g2012", "-o", vvp, *[f"-D{m}" for m in a.define], *rtl, *a.extra, os.path.join(HERE, "tb.sv")], check=True)
    try:
        sim = subprocess.run(["vvp", "-n", vvp, f"+dir={a.out}", f"+nprog={a.nprog}", f"+nst={a.nst}", f"+seed={a.seed}",
                              f"+rdy={a.rdy}", f"+irq={a.irq}", f"+nmi={a.nmi}"], capture_output=True, text=True, timeout=a.timeout)
    except subprocess.TimeoutExpired:
        print(f"FAIL: simulation still running after {a.timeout:.0f} s (hang)"); return 1
    if "DONE c8 tb" not in sim.stdout:
        print(sim.stdout[-2000:], sim.stderr[-2000:]); print("FAIL: simulator problems"); return 1
    bad = reset_stack = 0
    tot = {"cycles": 0, "instructions": 0, "IRQ": 0, "NMI": 0, "stopped": 0, "rdy_holds": 0}
    for p, mem in enumerate(progs):
        lines = [l.split() for l in open(f"{a.out}/prog{p}/pins.txt")]
        err, st = compare(mem, lines)
        for k in tot: tot[k] += st.get(k, 0)
        if "reset_stack" in st:
            reset_stack += 1
            if reset_stack == 1:
                print(f"note prog{p}: reset cycles 3-5 read {st['reset_stack']}, spec {{01,S}} {{01,S-1}} {{01,S-2}}")
        if err:
            bad += 1
            if bad <= 10:
                print(f"MISMATCH prog{p} (seed {a.seed}, program {p}): {err}")
    print(f"compared: {tot['cycles']} cycles, {tot['instructions']} instructions "
          f"({tot['instructions'] // max(1, a.nprog)} per program), IRQ {tot['IRQ']}, NMI {tot['NMI']}, "
          f"RDY-held reads {tot['rdy_holds']}, stopped at an undocumented byte: {tot['stopped']}")
    # spec §5 (#30) doesn't compare a in reset cycles 3-5; the S, S-1, S-2 pattern is reported, not failed
    print(f"note (not a spec check): reset cycles 3-5 not at S, S-1, S-2 in {reset_stack} programs")
    print(f"c8: seed={a.seed} programs={a.nprog} cycles={a.nst} mismatching_programs={bad}")
    ok = bad == 0
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
