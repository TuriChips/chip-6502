#!/usr/bin/env python3
"""Vectors for a block-level check of m6502_alu (blocks.md section 3, op table of PR #9): expected results from tests/mach6502.py (written from spec 4.1/6.1/6 only).
Each vector: reset (A = 0, I = 1, N = V = Z = 0, D = C = 0, spec 5/blocks), optionally SED / SEC, LD a, then `op` with a_in = a (A) and b: expected a_out, P (as pushed, B = push_b),
`result` for the ops where blocks.md defines it. Two 48-bit hex words per vector: control {chk_res[47], chk_a[46], op[45:41], a[40:33], b[32:25], c[24], d[23], pb[22]} and expected {exp_res[23:16], exp_a[15:8], exp_p[7:0]}.
ADC and SBC: every a x every b x c x d (262,144 vectors each). Other ops: every b with a in a spread of 24 values, c, d (and flag-op cases)."""
import os, sys
sys.dont_write_bytecode = True
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here + '/..')
import mach6502 as M
out = sys.argv[1] if len(sys.argv) > 1 else "build/alu_vectors.hex"; os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
AS = [0x00, 0x01, 0x0F, 0x10, 0x3E, 0x55, 0x7F, 0x80, 0x81, 0x8F, 0x99, 0xAA, 0xB4, 0xF0, 0xF9, 0xFF, 0x09, 0x0A, 0x19, 0x20, 0x40, 0x7E, 0xC0, 0xFE]
def model(op, a, b, c, d):
    m = M.Mach(0); m.a = a; m.c = c; m.d = d; m.n = m.v = m.z = 0; m.i = 1; res = None
    if op == 1: m.adc(b)
    elif op == 2: m.sbc(b)
    elif op == 3: m.a = a & b; m.nz(m.a)
    elif op == 4: m.a = a | b; m.nz(m.a)
    elif op == 5: m.a = a ^ b; m.nz(m.a)
    elif op == 6: m.cmp(a, b); res = (a - b) & 255
    elif op == 7: m.z = 1 if a & b == 0 else 0; m.n = b >> 7; m.v = b >> 6 & 1; res = a & b
    elif op in (8, 9, 10, 11, 12, 13): res = m.rmw({8: 'ASL', 9: 'LSR', 10: 'ROL', 11: 'ROR', 12: 'INC', 13: 'DEC'}[op], b)
    elif op == 14: res = b; m.nz(b)
    elif op == 15: m.c = 0
    elif op == 16: m.c = 1
    elif op == 17: m.i = 0
    elif op == 18: m.i = 1
    elif op == 19: m.d = 0
    elif op == 20: m.d = 1
    elif op == 21: m.v = 0
    writes_a = op in (1, 2, 3, 4, 5)
    return res, (m.a if writes_a else a), m
n = 0
with open(out, "w") as f:
    def emit(op, a, b, c, d):
        global n
        pb = (a ^ b) & 1; res, ea, m = model(op, a, b, c, d); chk_res = res is not None; chk_a = op in (1, 2, 3, 4, 5)
        f.write("%012X\n" % (chk_res << 47 | chk_a << 46 | op << 41 | a << 33 | b << 25 | c << 24 | d << 23 | pb << 22 | 0))
        f.write("%012X\n" % ((res or 0) << 16 | ea << 8 | m.p(pb)))
        n += 1
    for op in (1, 2):
        for a in range(256):
            for b in range(256):
                for c in (0, 1):
                    for d in (0, 1): emit(op, a, b, c, d)
    for op in range(3, 22):
        for a in AS:
            for b in range(256):
                for c in (0, 1):
                    for d in (0, 1): emit(op, a, b, c, d)
print(f"wrote {n} vectors to {out}")
