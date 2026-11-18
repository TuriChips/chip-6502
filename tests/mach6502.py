#!/usr/bin/env python3
"""Cycle-accurate 6502 model written from docs/spec.md only: section 4.1 (Appendix A per-cycle tables), section 6.1 (instructions), the section 6 decimal-mode
Decision (Clark's NMOS prediction), the B-flag and JMP-indirect rules. It reads no RTL and is not Beru's reference model (ref/).
Mach.step() executes one instruction and returns its cycles: a list of (addr, rw, data, sync); rw 1 = read, 0 = write; data = the byte read or written
(for a read, the byte the memory returned); sync 1 on the opcode fetch. Interrupt sequences and RESET are not modelled here (C4/C6)."""
import sys, os
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import asm6502
INV = {v: k for k, v in asm6502.OPS.items()}          # opcode -> (mnemonic, mode)
READ = {'ADC', 'AND', 'BIT', 'CMP', 'CPX', 'CPY', 'EOR', 'LDA', 'LDX', 'LDY', 'ORA', 'SBC'}
STORE = {'STA', 'STX', 'STY'}
RMW = {'ASL', 'DEC', 'INC', 'LSR', 'ROL', 'ROR'}
BR = {'BPL': ('N', 0), 'BMI': ('N', 1), 'BVC': ('V', 0), 'BVS': ('V', 1), 'BCC': ('C', 0), 'BCS': ('C', 1), 'BNE': ('Z', 0), 'BEQ': ('Z', 1)}
class Mach:
    def __init__(s, pc=0, mem=None):
        s.a = s.x = s.y = 0; s.s = 0xFF; s.pc = pc; s.mem = mem if mem is not None else {}
        s.n = s.v = s.d = s.i = s.z = s.c = 0
        s.rom_from = 0x10000           # addresses at or above this are ROM: writes are put on the bus but not stored (tests use 0x8000)
    # --- state helpers
    def p(s, b=0):                                   # P as pushed: bit 5 = 1, bit 4 = b
        return s.n << 7 | s.v << 6 | 1 << 5 | b << 4 | s.d << 3 | s.i << 2 | s.z << 1 | s.c
    def setp(s, v): s.n, s.v, s.d, s.i, s.z, s.c = v >> 7 & 1, v >> 6 & 1, v >> 3 & 1, v >> 2 & 1, v >> 1 & 1, v & 1   # bits 4 and 5 are not stored
    def nz(s, v): s.n = v >> 7 & 1; s.z = 1 if v & 255 == 0 else 0
    def rd(s, a): return s.mem.get(a & 0xFFFF, 0)
    # --- ALU
    def adc(s, m):
        a, c = s.a, s.c; t = a + m + c; s.z = 1 if t & 255 == 0 else 0      # binary Z (also the decimal Z, spec 6)
        if not s.d:
            s.v = (~(a ^ m) & (a ^ t) & 0x80) >> 7; s.n = (t >> 7) & 1; s.c = t >> 8; s.a = t & 255; return
        lo = (a & 15) + (m & 15) + c; hc = 0
        if lo >= 10: lo = (lo + 6) & 15; hc = 1
        x = (a & 0xF0) | lo; y = (m & 0xF0) | (0x0F if hc else 0); t2 = x + y + hc; r = t2 & 255
        s.n = r >> 7; s.v = (~(x ^ y) & (x ^ r) & 0x80) >> 7; cc = t2 >> 8
        if cc or r >= 0xA0: t3 = r + 0x60; s.a = t3 & 255; s.c = 1 if (cc or t3 >> 8) else 0
        else: s.a = r; s.c = 0
    def sbc(s, m):
        a, c = s.a, s.c; t = a + (~m & 255) + c; r = t & 255      # N V Z C as the binary SBC (spec 6)
        s.v = ((a ^ m) & (a ^ r) & 0x80) >> 7; s.n = r >> 7; s.z = 1 if r == 0 else 0; s.c = t >> 8
        if not s.d: s.a = r; return
        lo = (a & 15) - (m & 15) - (1 - c); hb = 0
        if lo < 0: lo = (lo - 6) & 15; hb = 1
        x = (a & 0xF0) | lo; y = (m & 0xF0) | (0x0F if hb else 0); t2 = x - y - hb
        if t2 < 0: t2 -= 0x60
        s.a = t2 & 255
    def cmp(s, r, m): t = r - m; s.c = 1 if r >= m else 0; s.nz(t & 255)
    def rmw(s, op, v):
        if op == 'ASL': s.c = v >> 7; v = (v << 1) & 255
        elif op == 'LSR': s.c = v & 1; v >>= 1
        elif op == 'ROL': c = s.c; s.c = v >> 7; v = ((v << 1) | c) & 255
        elif op == 'ROR': c = s.c; s.c = v & 1; v = (v >> 1) | (c << 7)
        elif op == 'INC': v = (v + 1) & 255
        else: v = (v - 1) & 255
        s.nz(v); return v
    def exec_read(s, op, m):
        if op == 'LDA': s.a = m; s.nz(m)
        elif op == 'LDX': s.x = m; s.nz(m)
        elif op == 'LDY': s.y = m; s.nz(m)
        elif op == 'AND': s.a &= m; s.nz(s.a)
        elif op == 'ORA': s.a |= m; s.nz(s.a)
        elif op == 'EOR': s.a ^= m; s.nz(s.a)
        elif op == 'ADC': s.adc(m)
        elif op == 'SBC': s.sbc(m)
        elif op == 'CMP': s.cmp(s.a, m)
        elif op == 'CPX': s.cmp(s.x, m)
        elif op == 'CPY': s.cmp(s.y, m)
        elif op == 'BIT': s.z = 1 if s.a & m == 0 else 0; s.n = m >> 7; s.v = m >> 6 & 1
    # --- the instruction
    def step(s):
        cyc = s._step(); s.pc &= 0xFFFF; return cyc
    def _step(s):
        cyc = []
        def rd(addr, sync=0):
            addr &= 0xFFFF; v = s.rd(addr); cyc.append((addr, 1, v, sync)); return v
        def wr(addr, v):
            addr &= 0xFFFF; v &= 255
            if addr < s.rom_from: s.mem[addr] = v
            cyc.append((addr, 0, v, 0))
        pc = s.pc; opc = rd(pc, 1); m, mode = INV[opc]
        if mode in ('imp', 'acc') and m not in ('PHA', 'PHP', 'PLA', 'PLP', 'RTS', 'RTI', 'BRK'):
            rd(pc + 1); s.pc = pc + 1                                  # A.1: dummy read of the next byte
            if m == 'ASL' or m == 'LSR' or m == 'ROL' or m == 'ROR': s.a = s.rmw(m, s.a)
            elif m == 'CLC': s.c = 0
            elif m == 'SEC': s.c = 1
            elif m == 'CLD': s.d = 0
            elif m == 'SED': s.d = 1
            elif m == 'CLI': s.i = 0
            elif m == 'SEI': s.i = 1
            elif m == 'CLV': s.v = 0
            elif m == 'DEX': s.x = (s.x - 1) & 255; s.nz(s.x)
            elif m == 'DEY': s.y = (s.y - 1) & 255; s.nz(s.y)
            elif m == 'INX': s.x = (s.x + 1) & 255; s.nz(s.x)
            elif m == 'INY': s.y = (s.y + 1) & 255; s.nz(s.y)
            elif m == 'TAX': s.x = s.a; s.nz(s.x)
            elif m == 'TAY': s.y = s.a; s.nz(s.y)
            elif m == 'TSX': s.x = s.s; s.nz(s.x)
            elif m == 'TXA': s.a = s.x; s.nz(s.a)
            elif m == 'TXS': s.s = s.x
            elif m == 'TYA': s.a = s.y; s.nz(s.a)
            elif m == 'NOP': pass
            return cyc
        if m in BR:
            flag, want = BR[m]; off = rd(pc + 1); off = off - 256 if off >= 128 else off; base = (pc + 2) & 0xFFFF
            if getattr(s, flag.lower()) == want:
                tgt = (base + off) & 0xFFFF
                rd(base)                                                  # spec A.5.8 as amended (chip-6502#19/#21): taken T2 = PC+2
                if tgt >> 8 != base >> 8: rd((base & 0xFF00) | (tgt & 0xFF))     # page cross: T3 = {(PC+2)H, (PC+2+offset)L}, the uncarried target
                s.pc = tgt
            else: s.pc = base
            return cyc
        if m == 'PHA' or m == 'PHP':
            rd(pc + 1); wr(0x100 + s.s, s.a if m == 'PHA' else s.p(1)); s.s = (s.s - 1) & 255; s.pc = pc + 1; return cyc
        if m == 'PLA' or m == 'PLP':
            rd(pc + 1); rd(0x100 + s.s); s.s = (s.s + 1) & 255; v = rd(0x100 + s.s); s.pc = pc + 1
            if m == 'PLA': s.a = v; s.nz(v)
            else: s.setp(v)
            return cyc
        if m == 'JSR':
            adl = rd(pc + 1); rd(0x100 + s.s); ret = (pc + 2) & 0xFFFF
            wr(0x100 + s.s, ret >> 8); wr(0x100 + ((s.s - 1) & 255), ret & 255); adh = rd(pc + 2); s.s = (s.s - 2) & 255; s.pc = adh << 8 | adl; return cyc
        if m == 'BRK':
            rd(pc + 1); ret = (pc + 2) & 0xFFFF; wr(0x100 + s.s, ret >> 8); wr(0x100 + ((s.s - 1) & 255), ret & 255); wr(0x100 + ((s.s - 2) & 255), s.p(1))
            s.s = (s.s - 3) & 255; lo = rd(0xFFFE); hi = rd(0xFFFF); s.i = 1; s.pc = hi << 8 | lo; return cyc
        if m == 'RTI':
            rd(pc + 1); rd(0x100 + s.s); p = rd(0x100 + ((s.s + 1) & 255)); lo = rd(0x100 + ((s.s + 2) & 255)); hi = rd(0x100 + ((s.s + 3) & 255))
            s.s = (s.s + 3) & 255; s.setp(p); s.pc = hi << 8 | lo; return cyc
        if m == 'RTS':
            rd(pc + 1); rd(0x100 + s.s); lo = rd(0x100 + ((s.s + 1) & 255)); hi = rd(0x100 + ((s.s + 2) & 255)); rd(hi << 8 | lo)
            s.s = (s.s + 2) & 255; s.pc = ((hi << 8 | lo) + 1) & 0xFFFF; return cyc
        if m == 'JMP':
            if mode == 'abs': lo = rd(pc + 1); hi = rd(pc + 2); s.pc = hi << 8 | lo
            else:
                ial = rd(pc + 1); iah = rd(pc + 2); lo = rd(iah << 8 | ial); hi = rd(iah << 8 | ((ial + 1) & 255)); s.pc = hi << 8 | lo
            return cyc
        # --- memory-addressing instructions: build the effective address with the Appendix A cycles
        size = 3 if mode in ('abs', 'absx', 'absy') else 1 if mode == 'imm' and False else 2
        if mode == 'imm': v = rd(pc + 1); s.pc = pc + 2; s.exec_read(m, v); return cyc
        idx = s.x if mode in ('zpx', 'absx') else s.y
        if mode == 'zp': ea = rd(pc + 1)
        elif mode in ('zpx', 'zpy'): bal = rd(pc + 1); rd(bal); ea = (bal + idx) & 255
        elif mode == 'abs': lo = rd(pc + 1); hi = rd(pc + 2); ea = hi << 8 | lo
        elif mode in ('absx', 'absy'):
            bal = rd(pc + 1); bah = rd(pc + 2); low = (bal + idx) & 255; cross = (bal + idx) > 255; ea = ((bah + (1 if cross else 0)) & 255) << 8 | low
            if m in READ and not cross: s.pc = pc + 3; v = rd(bah << 8 | low); s.exec_read(m, v); return cyc          # 4 cycles
            if m in READ: rd(bah << 8 | low); s.pc = pc + 3; v = rd(ea); s.exec_read(m, v); return cyc                  # page cross: dummy then the real read
            rd(bah << 8 | low)                                                                                             # stores and RMW: always the dummy read
        elif mode == 'indx': bal = rd(pc + 1); rd(bal); adl = rd((bal + s.x) & 255); adh = rd((bal + s.x + 1) & 255); ea = adh << 8 | adl
        elif mode == 'indy':
            ial = rd(pc + 1); bal = rd(ial); bah = rd((ial + 1) & 255); low = (bal + s.y) & 255; cross = (bal + s.y) > 255; ea = ((bah + (1 if cross else 0)) & 255) << 8 | low
            if m in READ and not cross: s.pc = pc + 2; v = rd(bah << 8 | low); s.exec_read(m, v); return cyc
            if m in READ: rd(bah << 8 | low); s.pc = pc + 2; v = rd(ea); s.exec_read(m, v); return cyc
            rd(bah << 8 | low)
        s.pc = pc + (3 if mode in ('abs', 'absx', 'absy') else 2)
        if m in READ: v = rd(ea); s.exec_read(m, v)
        elif m in STORE: wr(ea, {'STA': s.a, 'STX': s.x, 'STY': s.y}[m])
        else: v = rd(ea); wr(ea, v); wr(ea, s.rmw(m, v))
        return cyc
