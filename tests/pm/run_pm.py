#!/usr/bin/env python3
"""Spec 9 item 3: examples from the MOS Programming Manual (6500-50A, Jan 1976), typed in by us from the page images, assembled with tests/asm6502.py and run on the RTL
(m6502_system, tb/tb_pm6502.sv, Icarus 4-state). Each program writes what the manual prints (and nothing else) to $7000; EXP is that printed value. Usage: run_pm.py [outdir]
Page numbers are the PRINTED page numbers. Scaffolding that is ours, not the manual's, is marked 'ours' (the data, the result dump, the final spin loop).
Flags are read with PHP/PLA/AND: C = bit 0 (mask $01), V = bit 6 (mask $40); a printed 'Carry = 0/1', 'Overflow = 0/1' becomes the masked byte."""
import os, subprocess, sys
sys.dont_write_bytecode = True
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here + '/..')
import asm6502 as A

TAIL = "\nend:    JMP end\n.org 0xFFFA\n.word 0x8000, 0x8000, 0x8000\n"      # ours: spin, vectors (reset -> $8000)
def flags(mask):   # ours: write the masked P to $7000 (PHP/PLA do not change C or V)
    return f"        PHP\n        PLA\n        AND #{mask}\n        STA $7000\n"
def bits(s): return int(s.replace(' ', ''), 2)

E = []   # (id, manual page, what the manual prints, asm, expected bytes, timing or None)
def add(i, page, printed, asm, exp, timing=None): E.append((i, page, printed, ".org 0x8000\n" + asm + TAIL, exp, timing))

# ---- Chapter 2: one run per printed result. A = accumulator result, then the flags the manual prints.
add("2.1", 7, "13 + 211 + carry-in 1 = 225 (E1), Carry 0", "SEC\nLDA #13\nADC #211\nSTA $7000\n" + flags("$01"), [0xE1, 0x00])
add("2.2", 8, "254 + 6 + carry-in 1 = 5, Carry 1 (256 + 5 = 261)", "SEC\nLDA #254\nADC #6\nSTA $7000\n" + flags("$01"), [0x05, 0x01])
# Example 2.3's listing (LDA L1, CLC, ADC L2, STA L3, LDA H1, ADC H2, STA H3), run with Example 2.4's and 2.5's numbers; ours: the PHP probes of the carry the manual prints, placed after each STA so A is not disturbed.
L2_3 = """.org 0x10
.byte {l1}, {h1}, {l2}, {h2}
        .org 0x8000
        LDA $10          ; L1
        CLC
        ADC $12          ; L2
        STA $14          ; L3
{p1}        LDA $11          ; H1
        ADC $13          ; H2
        STA $15          ; H3
{p2}        LDA $14
        STA $7000
        LDA $15
        STA $7000
"""
def ex23(l1, h1, l2, h2): return L2_3.format(l1=l1, h1=h1, l2=l2, h2=h2, p1=flags("$01"), p2=flags("$01")).replace(".org 0x8000\n        .org 0x8000", ".org 0x8000")
E.append(("2.3 / 2.4", 9, "258 + 4112 = 4370 (0x1112), carry after the low add 0, after the high add 0", ex23(0x02, 0x01, 0x10, 0x10) + TAIL, [0x00, 0x00, 0x12, 0x11], None))
E.append(("2.3 / 2.5", 10, "384 + 128 = 512 (0x0200), carry after the low add 1, after the high add 0", ex23(0x80, 0x01, 0x80, 0x00) + TAIL, [0x01, 0x00, 0x00, 0x02], None))
for i, page, pr, a, b, ex, fl in [
    ("2.6", 11, "+5 + +7 = +12 (0C), Carry 0, Overflow 0", 5, 7, 0x0C, 0x00),
    ("2.7", 12, "+127 + +2 = 1000 0001 (81), Carry 0, Overflow 1", 0x7F, 2, 0x81, 0x40),
    ("2.8", 12, "+5 + -3 = +2 (02), Carry 1, Overflow 0", 5, 0xFD, 0x02, 0x01),
    ("2.9", 12, "+5 + -7 = -2 (FE), Carry 0, Overflow 0", 5, 0xF9, 0xFE, 0x00),
    ("2.10", 12, "-5 + -7 = -12 (F4), Carry 1, Overflow 0", 0xFB, 0xF9, 0xF4, 0x01),
    ("2.11", 13, "-66 + -65 = 0111 1101 (7D), Carry 1, Overflow 1", 0xBE, 0xBF, 0x7D, 0x41)]:
    add(i, page, pr, f"CLC\nLDA #{a}\nADC #{b}\nSTA $7000\n" + flags("$41"), [ex, fl])
add("2.12", 13, "decimal 79 + 14 = 93 (BCD 93)", "CLC\nSED\nLDA #0x79\nADC #0x14\nSTA $7000", [0x93])
add("2.13", 15, "5 - 3 = +2, Carry 1 (no borrow)", "SEC\nLDA #5\nSBC #3\nSTA $7000\n" + flags("$01"), [0x02, 0x01])
add("2.14", 16, "5 - 6 = -1 (FF), Carry 0 (borrow)", "SEC\nLDA #5\nSBC #6\nSTA $7000\n" + flags("$01"), [0xFF, 0x00])
L2_15 = """.org 0x10
.byte {l1}, {h1}, {l2}, {h2}
        .org 0x8000
        SEC
        LDA $10
        SBC $12
        STA $14
{p}        LDA $11
        SBC $13
        STA $15
{p}        LDA $14
        STA $7000
        LDA $15
        STA $7000
"""
def ex215(l1, h1, l2, h2): return L2_15.format(l1=l1, h1=h1, l2=l2, h2=h2, p=flags("$01")).replace(".org 0x8000\n        .org 0x8000", ".org 0x8000") + TAIL
E.append(("2.15 / 2.16", 17, "512 - 255 = +257 (0x0101): low byte 01 with Carry 0, high byte 01 with Carry 1", ex215(0x00, 0x02, 0xFF, 0x00), [0x00, 0x01, 0x01, 0x01], None))
E.append(("2.15 / 2.17", 18, "255 - 512 = -257 (0xFEFF): low byte FF with Carry 1, high byte FE with Carry 0", ex215(0xFF, 0x00, 0x00, 0x02), [0x01, 0x00, 0xFF, 0xFE], None))
add("2.18", 19, "decimal 44 - 29 = 15 (BCD 15)", "SED\nSEC\nLDA #0x44\nSBC #0x29\nSTA $7000", [0x15])
for x in (0, 1):
    add(f"2.19 (X={x})", 21, "1100 X111 AND 1111 0111 = 1100 0111", f"LDA #{bits('1100 0111') | x << 3}\nAND #0b11110111\nSTA $7000", [bits('1100 0111')])
    add(f"2.20 (X={x})", 21, "1110 X111 ORA 0000 1000 = 1110 1111", f"LDA #{bits('1110 0111') | x << 3}\nORA #0b00001000\nSTA $7000", [bits('1110 1111')])
add("2.21", 22, "1010 1111 EOR 1111 1111 = 0101 0000", "LDA #0b10101111\nEOR #0b11111111\nSTA $7000", [bits('0101 0000')])

# ---- Chapter 6: moving five bytes. FIELD 1 = $10-$14, FIELD 2 = $20-$24 (zero page, as the manual assumes on p.70/72/73). The manual prints no data, so the data is ours; what it prints is
# 'the five values are moved'. Ours: sentinels EE at $1F and $25, to see nothing else is written, and the dump of $1F-$25.
DATA = ".org 0x10\n.byte 0x11, 0x22, 0x33, 0x44, 0x55\n.org 0x1F\n.byte 0xEE\n.org 0x25\n.byte 0xEE\n"
DUMP = "        LDX #0\ndump:   LDA $1F,X\n        STA $7000\n        INX\n        CPX #7\n        BNE dump\n"
MOVED = [0xEE, 0x11, 0x22, 0x33, 0x44, 0x55, 0xEE]
ex61 = "".join(f"        LDA ${0x10 + k:02X}\n        STA ${0x20 + k:02X}\n" for k in range(5))
add("6.1", 70, "five values moved by 10 instructions; zero page: 30 cycles (p.74)", DATA + ".org 0x8000\nSTART:\n" + ex61 + "FIN:\n" + DUMP, MOVED, ("START", "FIN", 30))
add("6.2", 72, "the loop moves the five values (self-modifying: START+1 and OTHER+1 are the operands; CLC, LDA FIELD1, ..., CMP #FIELD2+5, BNE START)", DATA + """.org 0x8000
INITIALIZE: CLC
START:  LDA $10
OTHER:  STA $20
        LDA START+1
        ADC #1
        STA START+1
        LDA OTHER+1
        ADC #1
        STA OTHER+1
        CMP #0x25
        BNE START
""" + DUMP, MOVED)
add("6.4", 76, "five values moved with index X (LDX #0, LDA FIELD1,X, STA FIELD2,X, INX, CPX #5, BNE); 15 cycles per value for zero page (p.77: 'from 15 cycles')",
    DATA + ".org 0x8000\n        LDX #0\nLOOP:   LDA $10,X\n        STA $20,X\n        INX\n        CPX #5\n        BNE LOOP\nFIN:\n" + DUMP, MOVED, ("LOOP", "FIN", 5 * 15 - 1))
add("6.5", 77, "five values moved counting X down (LDX #5, LDA FIELD1-1,X, STA FIELD2-1,X, DEX, BNE); 13 cycles per value for zero page (p.77: 'to 13 cycles')",
    DATA + ".org 0x8000\n        LDX #5\nLOOP:   LDA $0F,X\n        STA $1F,X\n        DEX\n        BNE LOOP\nFIN:\n" + DUMP, MOVED, ("LOOP", "FIN", 5 * 13 - 1))
# Example 6.16 (printed on p.94 as 'Example: 6.16', in the list of examples 6.15): LDX #BLOCK / LOOP LDA FROM-1,X / STA TO-1,X / DEX / BNE LOOP, N = 200, absolute fields.
pat = [(7 * i + 3) & 0xFF for i in range(200)]
d616 = ".org 0x2000\n.byte " + ",".join(map(str, pat)) + "\n.org 0x2FFF\n.byte 0xEE\n.org 0x30C8\n.byte 0xEE\n"
add("6.16 (p.94, N = 200)", 94, "N bytes moved, N < 256 (the manual prints the code and 'Memory Required: 11 Bytes'; no data)",
    d616.replace(".org 0x2000", ".org 0x2000") + ".org 0x8000\n        LDX #200\nLOOP:   LDA 0x1FFF,X\n        STA 0x2FFF,X\n        DEX\n        BNE LOOP\n"
    "        LDX #0\ndump:   LDA 0x2FFF,X\n        STA $7000\n        INX\n        CPX #202\n        BNE dump\n", [0xEE] + pat + [0xEE])

def run(outdir):
    os.makedirs(outdir, exist_ok=True); fails = 0
    root = os.path.dirname(os.path.dirname(here))
    rtl = [os.path.join(dp, f) for dp, _, fs in os.walk(os.environ.get('RTL_DIR', os.path.join(root, 'rtl'))) for f in sorted(fs) if f.endswith('.v')]
    for k, (i, page, printed, asm, exp, timing) in enumerate(E):
        tag = f"ex{k:02d}"; lines = asm.splitlines(); labels = {}
        A.assemble(lines, False, labels); mem = A.assemble(lines, True, labels)
        A.write_hex(mem, f"{outdir}/{tag}.hex"); open(f"{outdir}/{tag}.asm", "w").write(asm)
        open(f"{outdir}/{tag}.exp", "w").write("".join(f"{b:02X}\n" for b in exp))
        vvp = f"{outdir}/{tag}.vvp"
        r = subprocess.run(["iverilog", "-g2012", f'-DMEMFILE="{outdir}/{tag}.hex"', "-o", vvp, os.path.join(root, "tb/tb_pm6502.sv")] + rtl, capture_output=True, text=True)
        if r.returncode: print(f"FAIL Example {i}: iverilog: {r.stderr}"); fails += 1; continue
        args = ["vvp", "-n", vvp, f"+EXP={outdir}/{tag}.exp", f"+N={len(exp)}"]
        if timing: args += [f"+FROM={labels[timing[0]]:x}", f"+TO={labels[timing[1]]:x}", f"+CLOCKS={timing[2]}"]
        out = subprocess.run(args, capture_output=True, text=True).stdout.strip().splitlines()
        res = [l for l in out if l.startswith(("PASS", "FAIL"))]
        ok = bool(res) and res[0].startswith("PASS") and not any(l.startswith("FAIL") for l in out)
        print(f"{'PASS' if ok else 'FAIL'} Example {i} (p.{page}): {printed}: {res[0] if res else 'no result'}")
        for l in out:
            if l.startswith("FAIL") and not ok: print("   ", l)
        fails += not ok
    print(f"pm: {len(E)} programs, {fails} failing"); return fails

if __name__ == '__main__': sys.exit(1 if run(sys.argv[1] if len(sys.argv) > 1 else "build/pm") else 0)
