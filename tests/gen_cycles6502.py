#!/usr/bin/env python3
"""Generates seeded random-program tests on the m6502 pins (C1, C2, C4 in part): a random RAM image (0000-7FFF random bytes, 8000-FFFF ROM holding the program and the
vectors), a program of random documented instructions in every addressing mode (zero page, indexed, indirect pointers and effective addresses are random, so page
crossings, zero-page wraps, stack wraps and writes to anywhere in RAM all occur), control-flow macros (branches over a 2-byte pad, JSR to an inline RTS, JMP, JMP (xxFF),
RTI, BRK/IRQ-vector RTI) and the expected value of EVERY cycle (address, rw, sync, data written) from tests/mach6502.py (written from spec 4.1/6.1/6).
Memory above 8000 is ROM: writes appear on the bus but are not stored, in the testbench and in the model.
Output: <outdir>/cyc_s<seed>.asm, .hex (the memory image: RAM then program), .cyc: one line per cycle `AAAA R S DD` (R = rw, S = sync, DD = write data or xx).
Comparison starts at the first sync after reset (spec 5), preamble included: LDX #s; TXS; LDA #p; PHA; PLP; LDA #a; LDX #x; LDY #y (no register is read before it is written)."""
import os, random, sys
sys.dont_write_bytecode = True
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import asm6502 as A, mach6502 as M
d = sys.argv[1] if len(sys.argv) > 1 else "build/gen/c6502"; os.makedirs(d, exist_ok=True)
NOT_RANDOM = {'JMP', 'JSR', 'RTS', 'RTI', 'BRK', 'BPL', 'BMI', 'BVC', 'BVS', 'BCC', 'BCS', 'BNE', 'BEQ'}
PLAIN = [k for k in A.OPS if k[0] not in NOT_RANDOM]
BR = ['BPL', 'BMI', 'BVC', 'BVS', 'BCC', 'BCS', 'BNE', 'BEQ']
CODE = 0x8000; HANDLER = 0xF000
def operand(mode, rnd):
    r = rnd.randrange(256)
    return {'imp': '', 'acc': ' A', 'imm': f' #{r}', 'zp': f' ${r:02X}', 'zpx': f' ${r:02X},X', 'zpy': f' ${r:02X},Y', 'abs': f' ${rnd.randrange(0, 0x8000):04X}',
            'absx': f' ${rnd.randrange(0, 0x8000):04X},X', 'absy': f' ${rnd.randrange(0, 0x8000):04X},Y', 'indx': f' (${r:02X},X)', 'indy': f' (${r:02X}),Y'}[mode]
def program(rnd, n):
    L = [f".org {CODE:#06x}", f"        LDX #{rnd.randrange(256)}", "        TXS", f"        LDA #{rnd.randrange(256) & 0xCF}", "        PHA", "        PLP",
         f"        LDA #{rnd.randrange(256)}", f"        LDX #{rnd.randrange(256)}", f"        LDY #{rnd.randrange(256)}"]
    k = 0; lab = 0
    while len(L) < n:
        r = rnd.random()
        if r < 0.78:
            m, mode = rnd.choice(PLAIN); L.append("        " + m + operand(mode, rnd))
        elif r < 0.88: lab += 1; L += [f"        {rnd.choice(BR)} s{lab}", "        NOP", "        NOP", f"s{lab}:"]
        elif r < 0.92: lab += 1; L += [f"        JSR f{lab}", f"        JMP g{lab}", f"f{lab}:", "        RTS", f"g{lab}:"]
        elif r < 0.94: lab += 1; L += [f"        JMP g{lab}", f"g{lab}:"]
        elif r < 0.96:       # JMP ($20FF): the high byte comes from $2000 (page wrap), both set to point at the next instruction
            lab += 1; L += [f"        LDA #<g{lab}", "        STA $20FF", f"        LDA #>g{lab}", "        STA $2000", "        JMP ($20FF)", f"g{lab}:"]
        elif r < 0.98:       # RTI to the next instruction: push PCH, PCL, P
            lab += 1; L += [f"        LDA #>g{lab}", "        PHA", f"        LDA #<g{lab}", "        PHA", f"        LDA #{rnd.randrange(256) & 0xCF}", "        PHA", "        RTI", f"g{lab}:"]
        else: L += ["        BRK", "        NOP"]        # the IRQ/BRK vector points at an RTI; it returns to BRK + 2
    return L
def expand(lines):
    """resolve '#<label' / '#>label' for the assembler: two-pass by hand"""
    return lines
def build(seed, n=3000):
    rnd = random.Random(seed)
    src = program(rnd, n)
    labels = {}; text = src
    # '#<g1' and '#>g1': substitute after the first pass
    A.assemble([l.replace('#<', '#').replace('#>', '#') for l in text], False, labels)
    text = [l.replace('#<', '#') .replace('#>', '#') for l in text]
    out = []
    for l in src:
        if '#<' in l: lab = l.split('#<')[1].strip(); out.append(l.split('#<')[0] + f"#{labels[lab] & 255}")
        elif '#>' in l: lab = l.split('#>')[1].strip(); out.append(l.split('#>')[0] + f"#{labels[lab] >> 8}")
        else: out.append(l)
    src = out
    # end loop and vectors / handler
    src += ["end:    JMP end", f".org {HANDLER:#06x}", "        RTI", ".org 0xFFFA", f".word {HANDLER}, {CODE}, {HANDLER}"]
    labels = {}; A.assemble(src, False, labels); mem = A.assemble(src, True, labels)
    ram = {a: rnd.randrange(256) for a in range(0x8000)}
    image = dict(ram); image.update(mem)
    m = M.Mach(CODE); m.rom_from = 0x8000; m.mem = dict(image); m.i = 1; cycles = []
    end = labels['end']
    while m.pc != end and len(cycles) < 200000: cycles += m.step()
    return src, image, cycles
for seed in (1, 2, 3):
    src, image, cycles = build(seed)
    open(f"{d}/cyc_s{seed}.asm", "w").write("\n".join(src) + "\n")
    A.write_hex(image, f"{d}/cyc_s{seed}.hex")
    with open(f"{d}/cyc_s{seed}.cyc", "w") as f:
        for a, rw, v, sy in cycles: f.write("%04X %d %d %s\n" % (a, rw, sy, "xx" if rw else "%02X" % v))
    print(f"seed {seed}: {len(cycles)} cycles")
