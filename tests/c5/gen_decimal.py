#!/usr/bin/env python3
"""C5 at CPU level: decimal ADC and SBC (D = 1) over every A x every operand x both carries (131,072 cases each) executed by the m6502 RTL as a 6502 program with loops;
the expected A and pushed P come from tests/mach6502.py (spec section 6 decimal rules, Clark-based N/V/Z). Output <outdir>/dec_adc|dec_sbc .asm / .hex / .exp (the expected bytes, 2 per
case: the value written to $7000 (A) and $7001 (P as PHP pushes it: B = 1, bit 5 = 1, D = 1, I = 1 from reset)). The testbench tb_trace6502.sv compares the writes to those two addresses."""
import os, sys
sys.dont_write_bytecode = True
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here + '/..')
import asm6502 as A, mach6502 as M
d = sys.argv[1] if len(sys.argv) > 1 else "build/gen/c5"; os.makedirs(d, exist_ok=True)
for op in ('ADC', 'SBC'):
    src = f""".org 0x8000
        SED
        LDA #0
        STA $00          ; a
oa:     LDA #0
        STA $01          ; b
ob:     LDA #0
        STA $02          ; c
oc:     LDA $02
        LSR A            ; C = c
        LDA $00
        {op} $01
        STA $7000
        PHP
        PLA
        STA $7001
        INC $02
        LDA $02
        CMP #2
        BNE oc
        INC $01
        BNE ob
        INC $00
        BNE oa
end:    JMP end
.org 0xFFFA
.word 0x8000, 0x8000, 0x8000"""
    lines = src.splitlines(); labels = {}; A.assemble(lines, False, labels); mem = A.assemble(lines, True, labels)
    A.write_hex(mem, f"{d}/dec_{op.lower()}.hex"); open(f"{d}/dec_{op.lower()}.asm", "w").write(src + "\n")
    with open(f"{d}/dec_{op.lower()}.exp", "w") as f:
        for a in range(256):
            for b in range(256):
                for c in (0, 1):
                    m = M.Mach(0); m.d = 1; m.c = c; m.a = a
                    m.adc(b) if op == 'ADC' else m.sbc(b)
                    p = m.n << 7 | m.v << 6 | 0x20 | 0x10 | 0x08 | 0x04 | m.z << 1 | m.c
                    f.write("%02X\n%02X\n" % (m.a, p))
    print(f"{op}: {256 * 256 * 2} cases")
