#!/usr/bin/env python3
"""MOS 6502 reference model (Beru, chip-6502#6). Written from docs/spec.md only, never from the RTL.

One call to step() runs one instruction (or one interrupt sequence) and returns its bus cycles, one per
clock, exactly as spec §4.1 lists them: (addr, rw, data, sync). rw = 1 read / 0 write; data is the byte read
(from the read callback) or written; sync = 1 only on the opcode fetch (T0). Every dummy "(disc.)" cycle is
a real read through the callback, at the address the spec gives.

Spec references in comments: §4.1 A.x.y = the per-cycle table; §6 = instruction semantics and decimal mode.
Usage: python3 ref/ref6502.py   (selftest)
"""

class Undocumented(Exception):
    """One of the 105 "Future Expansion" bytes (§6.0): not specified, not tested."""


# §6.0 opcode map, row by row (hi nibble 0..F, lo 0..F). "." = Future Expansion.
_MAP = """
BRK.imp ORA.izx . . . ORA.zp ASL.zp . PHP.imp ORA.imm ASL.acc . . ORA.abs ASL.abs .
BPL.rel ORA.izy . . . ORA.zpx ASL.zpx . CLC.imp ORA.aby . . . ORA.abx ASL.abx .
JSR.abs AND.izx . . BIT.zp AND.zp ROL.zp . PLP.imp AND.imm ROL.acc . BIT.abs AND.abs ROL.abs .
BMI.rel AND.izy . . . AND.zpx ROL.zpx . SEC.imp AND.aby . . . AND.abx ROL.abx .
RTI.imp EOR.izx . . . EOR.zp LSR.zp . PHA.imp EOR.imm LSR.acc . JMP.abs EOR.abs LSR.abs .
BVC.rel EOR.izy . . . EOR.zpx LSR.zpx . CLI.imp EOR.aby . . . EOR.abx LSR.abx .
RTS.imp ADC.izx . . . ADC.zp ROR.zp . PLA.imp ADC.imm ROR.acc . JMP.ind ADC.abs ROR.abs .
BVS.rel ADC.izy . . . ADC.zpx ROR.zpx . SEI.imp ADC.aby . . . ADC.abx ROR.abx .
. STA.izx . . STY.zp STA.zp STX.zp . DEY.imp . TXA.imp . STY.abs STA.abs STX.abs .
BCC.rel STA.izy . . STY.zpx STA.zpx STX.zpy . TYA.imp STA.aby TXS.imp . . STA.abx . .
LDY.imm LDA.izx LDX.imm . LDY.zp LDA.zp LDX.zp . TAY.imp LDA.imm TAX.imp . LDY.abs LDA.abs LDX.abs .
BCS.rel LDA.izy . . LDY.zpx LDA.zpx LDX.zpy . CLV.imp LDA.aby TSX.imp . LDY.abx LDA.abx LDX.aby .
CPY.imm CMP.izx . . CPY.zp CMP.zp DEC.zp . INY.imp CMP.imm DEX.imp . CPY.abs CMP.abs DEC.abs .
BNE.rel CMP.izy . . . CMP.zpx DEC.zpx . CLD.imp CMP.aby . . . CMP.abx DEC.abx .
CPX.imm SBC.izx . . CPX.zp SBC.zp INC.zp . INX.imp SBC.imm NOP.imp . CPX.abs SBC.abs INC.abs .
BEQ.rel SBC.izy . . . SBC.zpx INC.zpx . SED.imp SBC.aby . . . SBC.abx INC.abx .
"""
OPS = {}
for _hi, _row in enumerate(_MAP.split("\n")[1:17]):
    for _lo, _cell in enumerate(_row.split()):
        if _cell != ".":
            _m, _mode = _cell.split(".")
            OPS[_hi * 16 + _lo] = (_m, _mode)
assert len(OPS) == 151
UNDOCUMENTED = frozenset(b for b in range(256) if b not in OPS)

READ_OPS = {"ADC", "AND", "BIT", "CMP", "CPX", "CPY", "EOR", "LDA", "LDX", "LDY", "ORA", "SBC"}   # §4.1 A.2
STORE_OPS = {"STA", "STX", "STY"}                                                                # A.3
RMW_OPS = {"ASL", "DEC", "INC", "LSR", "ROL", "ROR"}                                             # A.4
BRANCH = {"BPL": ("n", 0), "BMI": ("n", 1), "BVC": ("v", 0), "BVS": ("v", 1),
          "BCC": ("c", 0), "BCS": ("c", 1), "BNE": ("z", 0), "BEQ": ("z", 1)}


class CPU:
    def __init__(self, read, write):
        self.read, self.write = read, write
        self.a = self.x = self.y = 0
        self.s = 0xFF
        self.pc = 0
        self.n = self.v = self.d = self.i = self.z = self.c = 0
        self.cyc = []

    # --- P as a byte. B exists only in the pushed byte (§3); bit 5 is 1 when pushed.
    def p_byte(self, b):
        return (self.n << 7) | (self.v << 6) | 0x20 | (b << 4) | (self.d << 3) | (self.i << 2) | (self.z << 1) | self.c

    def set_p(self, v):
        self.n, self.v, self.d, self.i, self.z, self.c = (v >> 7) & 1, (v >> 6) & 1, (v >> 3) & 1, (v >> 2) & 1, (v >> 1) & 1, v & 1

    # --- bus
    def rd(self, addr, sync=0):
        addr &= 0xFFFF
        v = self.read(addr) & 0xFF
        self.cyc.append((addr, 1, v, sync))
        return v

    def wr(self, addr, v):
        addr &= 0xFFFF
        self.write(addr, v & 0xFF)
        self.cyc.append((addr, 0, v & 0xFF, 0))

    def push(self, v):
        self.wr(0x100 | self.s, v)
        self.s = (self.s - 1) & 0xFF

    def nz(self, v):
        self.n, self.z = (v >> 7) & 1, int(v == 0)
        return v

    # --- interrupt and reset sequences (§4 and A.5.4)
    def interrupt(self, nmi):
        """IRQ or NMI at an instruction boundary: 7 cycles, the first being the (discarded) opcode fetch."""
        self.cyc = []
        self.rd(self.pc, sync=1)                      # T0: fetch, opcode discarded ("Finish Previous Operation")
        self.rd(self.pc)                              # T1: PC again ("Hold P-Counter"), not PC+1
        self.push(self.pc >> 8); self.push(self.pc & 0xFF)
        self.push(self.p_byte(0))                     # B = 0 for IRQ (p.144) and NMI (§6 Decision)
        vec = 0xFFFA if nmi else 0xFFFE
        lo = self.rd(vec); hi = self.rd(vec + 1)
        self.i = 1                                     # set I in cycle 7 (Example 9.2)
        self.pc = (hi << 8) | lo
        return self.cyc

    def reset(self):
        """The 7 cycles after res_n rises (Example 9.1). Cycles 1-2: address not specified (None).
        Cycles 3-5: reads at {01,S}, {01,S-1}, {01,S-2}. S afterwards isn't compared (§3)."""
        self.cyc = [(None, 1, None, 0), (None, 1, None, 0)]
        for k in range(3):
            self.rd(0x100 | ((self.s - k) & 0xFF))
        self.s = (self.s - 3) & 0xFF
        lo = self.rd(0xFFFC); hi = self.rd(0xFFFD)
        self.i = 1
        self.pc = (hi << 8) | lo
        return self.cyc

    # --- ALU (§6.1, decimal per §6 option (a))
    def adc(self, m):
        a, c = self.a, self.c
        b = a + m + c
        if not self.d:
            self.v = int(((a ^ b) & (m ^ b) & 0x80) != 0)
            self.c = int(b > 0xFF)
            self.a = self.nz(b & 0xFF)
            return
        lo = (a & 0x0F) + (m & 0x0F) + c                         # step 1
        if lo >= 0x0A:
            lo, hc = (lo + 6) & 0x0F, 1
        else:
            hc = 0
        x = (a & 0xF0) | lo                                      # step 2
        y = (m & 0xF0) | (0x0F if hc else 0)
        t = x + y + hc
        self.n = (t >> 7) & 1
        self.v = int(((x ^ t) & (y ^ t) & 0x80) != 0)
        c1 = int(t > 0xFF)
        t &= 0xFF
        c2 = 0
        if c1 or t >= 0xA0:                                      # step 3
            t2 = t + 0x60
            c2 = int(t2 > 0xFF)
            t = t2 & 0xFF
        self.a = t
        self.c = int(c1 or c2)
        self.z = int((b & 0xFF) == 0)                            # step 4: Z from the binary sum

    def sbc(self, m):
        a, c = self.a, self.c
        b = a - m - (1 - c)                                      # binary: flags (both modes)
        self.c = int(b >= 0)
        self.v = int(((a ^ m) & (a ^ b) & 0x80) != 0)
        self.nz(b & 0xFF)
        if not self.d:
            self.a = b & 0xFF
            return
        lo = (a & 0x0F) - (m & 0x0F) - (1 - c)                   # decimal: A only
        if lo < 0:
            lo, hb = (lo - 6) & 0x0F, 1
        else:
            hb = 0
        t = ((a & 0xF0) | lo) - ((m & 0xF0) | (0x0F if hb else 0)) - hb
        if t < 0:
            t -= 0x60
        self.a = t & 0xFF

    def cmp(self, r, m):
        t = r - m
        self.c = int(t >= 0)
        self.nz(t & 0xFF)

    def rmw(self, op, v):
        if op == "ASL":
            self.c = v >> 7; v = (v << 1) & 0xFF
        elif op == "LSR":
            self.c = v & 1; v >>= 1
        elif op == "ROL":
            v, self.c = ((v << 1) | self.c) & 0xFF, v >> 7
        elif op == "ROR":
            v, self.c = (v >> 1) | (self.c << 7), v & 1
        elif op == "INC":
            v = (v + 1) & 0xFF
        elif op == "DEC":
            v = (v - 1) & 0xFF
        return self.nz(v)

    def do_read(self, op, m):
        if op == "LDA": self.a = self.nz(m)
        elif op == "LDX": self.x = self.nz(m)
        elif op == "LDY": self.y = self.nz(m)
        elif op == "AND": self.a = self.nz(self.a & m)
        elif op == "ORA": self.a = self.nz(self.a | m)
        elif op == "EOR": self.a = self.nz(self.a ^ m)
        elif op == "ADC": self.adc(m)
        elif op == "SBC": self.sbc(m)
        elif op == "CMP": self.cmp(self.a, m)
        elif op == "CPX": self.cmp(self.x, m)
        elif op == "CPY": self.cmp(self.y, m)
        elif op == "BIT":
            self.z = int((self.a & m) == 0); self.n = m >> 7; self.v = (m >> 6) & 1
        else:
            raise AssertionError(op)

    # --- one instruction
    def step(self):
        self.cyc = []
        pc = self.pc
        opc = self.rd(pc, sync=1)                                # T0
        if opc not in OPS:
            raise Undocumented(f"{opc:02X} at {pc:04X}")
        op, mode = OPS[opc]
        p1 = (pc + 1) & 0xFFFF

        if mode in ("imp", "acc"):                               # A.1, A.5.1/2/5/7, BRK
            return self.implied(op, pc)
        if mode == "rel":                                        # A.5.8
            off = self.rd(p1)
            nxt = (pc + 2) & 0xFFFF
            flag, want = BRANCH[op]
            if getattr(self, flag) != want:
                self.pc = nxt
                return self.cyc
            tgt = (nxt + (off - 256 if off & 0x80 else off)) & 0xFFFF
            self.rd((nxt & 0xFF00) | (tgt & 0xFF))               # T2: uncarried (disc.)
            if (tgt ^ nxt) & 0xFF00:
                self.rd(tgt)                                      # T3: with carry (disc.)
            self.pc = tgt
            return self.cyc
        if op == "JMP":
            lo = self.rd(p1); hi = self.rd(pc + 2)
            if mode == "abs":                                    # A.5.6.1
                self.pc = (hi << 8) | lo
            else:                                                # A.5.6.2: IAL+1 doesn't carry into IAH
                adl = self.rd((hi << 8) | lo)
                adh = self.rd((hi << 8) | ((lo + 1) & 0xFF))
                self.pc = (adh << 8) | adl
            return self.cyc
        if op == "JSR":                                          # A.5.3
            adl = self.rd(p1)
            self.rd(0x100 | self.s)                              # (disc.)
            ret = (pc + 2) & 0xFFFF
            self.push(ret >> 8); self.push(ret & 0xFF)
            adh = self.rd(pc + 2)
            self.pc = (adh << 8) | adl
            return self.cyc

        # memory operand modes
        store, rmw = op in STORE_OPS, op in RMW_OPS
        length = {"imm": 2, "zp": 2, "zpx": 2, "zpy": 2, "izx": 2, "izy": 2, "abs": 3, "abx": 3, "aby": 3}[mode]
        self.pc = (pc + length) & 0xFFFF
        if mode == "imm":                                        # A.2.1
            self.do_read(op, self.rd(p1))
            return self.cyc
        if mode == "zp":
            addr = self.rd(p1)
        elif mode in ("zpx", "zpy"):                             # A.2.6, A.3.5, A.4.3
            bal = self.rd(p1)
            self.rd(bal)                                         # {00, BAL} (disc.)
            addr = (bal + (self.x if mode == "zpx" else self.y)) & 0xFF
        elif mode == "abs":
            addr = self.rd(p1) | (self.rd(pc + 2) << 8)
        elif mode == "izx":                                      # A.2.4, A.3.3
            bal = self.rd(p1)
            self.rd(bal)                                         # (disc.)
            adl = self.rd((bal + self.x) & 0xFF)
            adh = self.rd((bal + self.x + 1) & 0xFF)
            addr = (adh << 8) | adl
        else:                                                    # abx, aby, izy: indexed with a possible page cross
            if mode == "izy":                                    # A.2.7, A.3.6
                ial = self.rd(p1)
                bal = self.rd(ial)
                bah = self.rd((ial + 1) & 0xFF)
                idx = self.y
            else:                                                # A.2.5, A.3.4, A.4.4
                bal = self.rd(p1); bah = self.rd(pc + 2)
                idx = self.x if mode == "abx" else self.y
            addr = ((bah << 8) + bal + idx) & 0xFFFF
            unc = (bah << 8) | ((bal + idx) & 0xFF)
            if store or rmw or unc != addr:
                self.rd(unc)                                     # dummy read at the uncarried address (disc.)
            elif not (store or rmw):
                pass
        if store:                                                # A.3
            self.wr(addr, {"STA": self.a, "STX": self.x, "STY": self.y}[op])
        elif rmw:                                                # A.4: read, write unmodified, write modified
            v = self.rd(addr)
            self.wr(addr, v)
            self.wr(addr, self.rmw(op, v))
        else:                                                    # A.2
            self.do_read(op, self.rd(addr))
        return self.cyc

    def implied(self, op, pc):
        p1 = (pc + 1) & 0xFFFF
        if op == "BRK":                                          # A.5.4, p.144
            self.rd(p1)                                          # (disc.)
            ret = (pc + 2) & 0xFFFF
            self.push(ret >> 8); self.push(ret & 0xFF)
            self.push(self.p_byte(1))
            lo = self.rd(0xFFFE); hi = self.rd(0xFFFF)
            self.i = 1
            self.pc = (hi << 8) | lo
            return self.cyc
        self.rd(p1)                                              # T1: next byte (disc.)
        if op in ("PHA", "PHP"):                                 # A.5.1
            self.push(self.a if op == "PHA" else self.p_byte(1))
            self.pc = p1
        elif op in ("PLA", "PLP"):                               # A.5.2
            self.rd(0x100 | self.s)                              # (disc.)
            self.s = (self.s + 1) & 0xFF
            v = self.rd(0x100 | self.s)
            if op == "PLA":
                self.a = self.nz(v)
            else:
                self.set_p(v)
            self.pc = p1
        elif op == "RTI":                                        # A.5.5
            self.rd(0x100 | self.s)
            self.s = (self.s + 1) & 0xFF; self.set_p(self.rd(0x100 | self.s))
            self.s = (self.s + 1) & 0xFF; lo = self.rd(0x100 | self.s)
            self.s = (self.s + 1) & 0xFF; hi = self.rd(0x100 | self.s)
            self.pc = (hi << 8) | lo
        elif op == "RTS":                                        # A.5.7
            self.rd(0x100 | self.s)
            self.s = (self.s + 1) & 0xFF; lo = self.rd(0x100 | self.s)
            self.s = (self.s + 1) & 0xFF; hi = self.rd(0x100 | self.s)
            self.rd((hi << 8) | lo)                              # (disc.)
            self.pc = (((hi << 8) | lo) + 1) & 0xFFFF
        else:                                                    # A.1, 2 cycles
            self.pc = p1
            if op in RMW_OPS:
                self.a = self.rmw(op, self.a)
            elif op == "CLC": self.c = 0
            elif op == "SEC": self.c = 1
            elif op == "CLI": self.i = 0
            elif op == "SEI": self.i = 1
            elif op == "CLD": self.d = 0
            elif op == "SED": self.d = 1
            elif op == "CLV": self.v = 0
            elif op == "TAX": self.x = self.nz(self.a)
            elif op == "TAY": self.y = self.nz(self.a)
            elif op == "TXA": self.a = self.nz(self.x)
            elif op == "TYA": self.a = self.nz(self.y)
            elif op == "TSX": self.x = self.nz(self.s)
            elif op == "TXS": self.s = self.x                    # no flags
            elif op == "INX": self.x = self.nz((self.x + 1) & 0xFF)
            elif op == "INY": self.y = self.nz((self.y + 1) & 0xFF)
            elif op == "DEX": self.x = self.nz((self.x - 1) & 0xFF)
            elif op == "DEY": self.y = self.nz((self.y - 1) & 0xFF)
            elif op == "NOP": pass
            else:
                raise AssertionError(op)
        return self.cyc


# ---------------------------------------------------------------- selftest
# Cycle counts per §6.1 (no page cross / branch not taken); "+p" modes checked with a cross separately.
CYCLES = {"imp": 2, "acc": 2, "imm": 2, "zp": 3, "zpx": 4, "zpy": 4, "abs": 4, "abx": 4, "aby": 4, "izx": 6,
          "izy": 5, "rel": 2}
SPECIAL = {"BRK": 7, "PHA": 3, "PHP": 3, "PLA": 4, "PLP": 4, "RTI": 6, "RTS": 6, "JSR": 6}


def _expected_cycles(op, mode):
    if op in SPECIAL: return SPECIAL[op]
    if op == "JMP": return 3 if mode == "abs" else 5
    if op in STORE_OPS: return {"abx": 5, "aby": 5, "izy": 6}.get(mode, CYCLES[mode] if mode not in ("zp", "abs") else (3 if mode == "zp" else 4))
    if op in RMW_OPS and mode != "acc": return {"zp": 5, "zpx": 6, "abs": 6, "abx": 7}[mode]
    return CYCLES[mode]


def selftest():
    fails = 0

    def check(cond, msg):
        nonlocal fails
        if not cond:
            fails += 1; print("FAIL", msg)

    # 1. cycle counts of all 151 opcodes, no page cross, branch not taken (§6.1 / §4.1)
    for opc, (op, mode) in OPS.items():
        mem = bytearray(65536)
        mem[0x0200] = opc; mem[0x0201] = 0x10; mem[0x0202] = 0x30
        c = CPU(mem.__getitem__, mem.__setitem__); c.pc = 0x0200; c.x = c.y = 1
        c.n = c.v = c.c = c.z = 0
        if op in BRANCH:                                    # make it not taken
            f, want = BRANCH[op]; setattr(c, f, 1 - want)
        n = len(c.step())
        check(n == _expected_cycles(op, mode), f"{opc:02X} {op} {mode}: {n} cycles, spec {_expected_cycles(op, mode)}")
    # 2. page cross: +1 for indexed reads, branches +1 / +2
    mem = bytearray(65536); mem[0x0200:0x0203] = bytes([0xBD, 0xFF, 0x30])           # LDA $30FF,X
    c = CPU(mem.__getitem__, mem.__setitem__); c.pc = 0x0200; c.x = 1
    cy = c.step(); check(len(cy) == 5 and cy[3][0] == 0x3000 and cy[4][0] == 0x3100, f"LDA abs,X cross: {cy}")
    mem = bytearray(65536); mem[0x02F0:0x02F2] = bytes([0xD0, 0x20])                   # BNE +$20 across a page
    c = CPU(mem.__getitem__, mem.__setitem__); c.pc = 0x02F0; c.z = 0
    cy = c.step(); check([x[0] for x in cy] == [0x02F0, 0x02F1, 0x0212, 0x0312] and c.pc == 0x0312, f"BNE cross: {cy}")
    # 3. JMP ($30FF) reads the high byte from $3000 (§6)
    mem = bytearray(65536); mem[0x0200:0x0203] = bytes([0x6C, 0xFF, 0x30]); mem[0x30FF] = 0x34; mem[0x3000] = 0x12
    c = CPU(mem.__getitem__, mem.__setitem__); c.pc = 0x0200; c.step(); check(c.pc == 0x1234, f"JMP ind wrap: {c.pc:04X}")
    # 4. decimal: the §6 example $99 + $01 → A=00 C=1 Z=0; Example 2.12 79 + 14 = 93
    c = CPU(None, None); c.d = 1; c.a = 0x99; c.c = 0; c.adc(0x01); check((c.a, c.c, c.z) == (0, 1, 0), f"99+01: {c.a:02X} {c.c} {c.z}")
    c.a = 0x79; c.c = 0; c.adc(0x14); check(c.a == 0x93, f"79+14 = {c.a:02X}")
    c.a = 0x00; c.c = 1; c.sbc(0x01); check((c.a, c.c) == (0x99, 0), f"00-01 = {c.a:02X} C={c.c}")
    print(("PASS" if not fails else f"FAIL ({fails})") + " ref6502 selftest: 151 opcodes' cycle counts, page cross, JMP wrap, decimal")
    return fails


if __name__ == "__main__":
    raise SystemExit(1 if selftest() else 0)
