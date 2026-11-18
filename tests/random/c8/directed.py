#!/usr/bin/env python3
"""Directed C8 cases (Beru, chip-6502#6): fixed programs and per-cycle stimulus for corners random C8 hits rarely,
judged against the model by run.compare() exactly like C8. Each case's stimulus is also checked against the §6
stimulus rule from the dumped pins: irq_n / nmi_n change only at an edge that starts a sync = 1 cycle, and nmi_n
stays low >= 2 cycles. Cases:
- nmi42-h<H>: chip-6502#42. An NMI is taken; nmi_n rises and falls again at the NMI sequence's T0 while RDY holds
  that T0 for H cycles. The second edge must stay pending (§6 rule 5).
- nmi43-f<F>: the #43 review. RDY holds the NMI sequence's T0 for 20 cycles while nmi_n falls F times (low 2, high
  2). One NMI must stay pending however many edges (§6 rule 3), including F = 4 (a 2-bit edge count wraps).
Usage: tests/random/c8/directed.py [--rtl DIR] [--out DIR]
"""
import argparse, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run

NST = 140
S = 22               # NOP@0203's fetch: reset released in cycle 10, LDX #FF 18-19, TXS 20-21 (no RDY before S)


def image():
    mem = bytearray(65536)
    mem[0xFFFC], mem[0xFFFD] = 0x00, 0x02
    mem[0xFFFA], mem[0xFFFB] = 0x00, 0x40
    mem[0xFFFE], mem[0xFFFF] = 0x00, 0x50
    mem[0x200:0x20A] = bytes([0xA2, 0xFF, 0x9A, 0xEA, 0xEA, 0xEA, 0xEA, 0x4C, 0x07, 0x02])   # LDX #FF; TXS; NOPx4; JMP 0207
    mem[0x4000:0x4005] = bytes([0xEA, 0xEA, 0x4C, 0x02, 0x40])                               # NMI: NOP; NOP; JMP 4002
    mem[0x5000:0x5003] = bytes([0x4C, 0x00, 0x50])
    return mem


def stim(nmi, rdy):
    """nmi(n), rdy(n) -> list of 'rdy irq nmi res' strings; res_n = 0 for cycles 0-9."""
    return [f"{rdy(n)}1{nmi(n)}{int(n >= 10)}" for n in range(NST)]


def cases():
    for h in (0, 1, 2, 3):
        # NMI falls at S (NOP@0203), taken after NOP@0204 (poll at S+2): sequence T0 at S+4. Rise at S+2, fall at S+4.
        yield f"nmi42-h{h}", (lambda n: 0 if n in (S, S + 1) or n >= S + 4 else 1), (lambda n, h=h: 0 if S + 4 <= n < S + 4 + h else 1)
    for f in (2, 3, 4, 5):
        def nmi(n, f=f):
            if n in (S, S + 1): return 0
            if n < S + 4: return 1
            k = n - (S + 4)
            return 0 if k >= 4 * (f - 1) or k % 4 < 2 else 1      # falls at S+4, S+8, ...; low from the last one on
        yield f"nmi43-f{f}", nmi, (lambda n: 0 if S + 4 <= n < S + 24 else 1)


def legal(lines):
    """§6 stimulus rule on the dumped run: changes only in a sync = 1 cycle; nmi_n low >= 2 cycles."""
    last_fall = None
    for i in range(11, len(lines)):
        for k, name in ((6, "irq_n"), (7, "nmi_n")):
            if lines[i][k] != lines[i - 1][k] and lines[i][8] == "1" and lines[i][2] != "1":
                return f"cycle {i}: {name} changed in a sync = 0 cycle"
        if lines[i][7] == "0" and lines[i - 1][7] == "1": last_fall = i
        if lines[i][7] == "1" and lines[i - 1][7] == "0" and last_fall is not None and i - last_fall < 2:
            return f"cycle {i}: nmi_n low for {i - last_fall} cycle(s)"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rtl", default=os.path.join(run.ROOT, "rtl"))
    ap.add_argument("--out", default=os.path.join(run.ROOT, "build", "directed"))
    ap.add_argument("--extra", nargs="*", default=[], help="extra Verilog files (gate level: PDK cell models)")
    ap.add_argument("--define", nargs="*", default=[], help="iverilog -D macros")
    a = ap.parse_args()
    rtl = sorted(os.path.join(dp, f) for dp, _, fs in os.walk(a.rtl) for f in fs if f.endswith(".v"))
    vvp = f"{a.out}/d.vvp"
    os.makedirs(a.out, exist_ok=True)
    subprocess.run(["iverilog", "-g2012", "-o", vvp, *[f"-D{m}" for m in a.define], *rtl, *a.extra,
                    os.path.join(HERE, "tb_directed.sv")], check=True)
    mem = image()
    bad = 0
    for name, nmi, rdy in cases():
        d = f"{a.out}/{name}"
        os.makedirs(d, exist_ok=True)
        open(f"{d}/mem.hex", "w").write("\n".join("%02x" % v for v in mem) + "\n")
        open(f"{d}/stim.txt", "w").write("\n".join(stim(nmi, rdy)) + "\n")
        r = subprocess.run(["vvp", "-n", vvp, f"+dir={d}", f"+nst={NST}"], capture_output=True, text=True)
        assert "DONE directed tb" in r.stdout, r.stdout[-500:]
        lines = [l.split() for l in open(f"{d}/pins.txt")]
        err = legal(lines)
        if err:
            print(f"BAD STIMULUS {name}: {err}"); bad += 1; continue
        err, st = run.compare(mem, lines)
        print(f"{'PASS' if not err else 'FAIL'} {name}: NMI sequences (model) {st['NMI']}" + (f" | {err}" if err else ""))
        bad += bool(err)
    print(("PASS" if not bad else f"FAIL ({bad})") + " directed C8")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
