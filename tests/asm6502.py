#!/usr/bin/env python3
"""Tiny 6502 assembler for the tests. The opcode table is the 151 documented opcodes of docs/spec.md section 6.0 (the MOS opcode map);
tests/asm6502_selftest.py checks it against the spec file itself, so a change to the spec's map is noticed.
Usage: asm6502.py prog.asm out.hex   -> $readmemh image with @address records (unlisted bytes are 00)
Syntax: ';' comments, 'label:', '.org N', '.byte V[,V..]', '.word V[,V..]' (little-endian). Numbers: decimal, 0x.., $hex, 0b..; label operands
and sums ('lab+1') allowed. Modes: 'LDA #n', 'LDA n' (zero page when a numeric literal < 256, else absolute; label operands are absolute;
'zp:label' / 'abs:n' force a mode), 'LDA n,X', 'LDA n,Y', 'LDA (n,X)', 'LDA (n),Y', 'JMP (n)', 'ASL A' (or 'ASL'), 'BNE label' (offset computed,
-128..127; a numeric operand is the target address), implied instructions without operand."""
import sys, re
sys.dont_write_bytecode = True

OPS = {
    ('BRK', 'imp'): 0x00,
    ('ORA', 'indx'): 0x01,
    ('ORA', 'zp'): 0x05,
    ('ASL', 'zp'): 0x06,
    ('PHP', 'imp'): 0x08,
    ('ORA', 'imm'): 0x09,
    ('ASL', 'acc'): 0x0A,
    ('ORA', 'abs'): 0x0D,
    ('ASL', 'abs'): 0x0E,
    ('BPL', 'rel'): 0x10,
    ('ORA', 'indy'): 0x11,
    ('ORA', 'zpx'): 0x15,
    ('ASL', 'zpx'): 0x16,
    ('CLC', 'imp'): 0x18,
    ('ORA', 'absy'): 0x19,
    ('ORA', 'absx'): 0x1D,
    ('ASL', 'absx'): 0x1E,
    ('JSR', 'abs'): 0x20,
    ('AND', 'indx'): 0x21,
    ('BIT', 'zp'): 0x24,
    ('AND', 'zp'): 0x25,
    ('ROL', 'zp'): 0x26,
    ('PLP', 'imp'): 0x28,
    ('AND', 'imm'): 0x29,
    ('ROL', 'acc'): 0x2A,
    ('BIT', 'abs'): 0x2C,
    ('AND', 'abs'): 0x2D,
    ('ROL', 'abs'): 0x2E,
    ('BMI', 'rel'): 0x30,
    ('AND', 'indy'): 0x31,
    ('AND', 'zpx'): 0x35,
    ('ROL', 'zpx'): 0x36,
    ('SEC', 'imp'): 0x38,
    ('AND', 'absy'): 0x39,
    ('AND', 'absx'): 0x3D,
    ('ROL', 'absx'): 0x3E,
    ('RTI', 'imp'): 0x40,
    ('EOR', 'indx'): 0x41,
    ('EOR', 'zp'): 0x45,
    ('LSR', 'zp'): 0x46,
    ('PHA', 'imp'): 0x48,
    ('EOR', 'imm'): 0x49,
    ('LSR', 'acc'): 0x4A,
    ('JMP', 'abs'): 0x4C,
    ('EOR', 'abs'): 0x4D,
    ('LSR', 'abs'): 0x4E,
    ('BVC', 'rel'): 0x50,
    ('EOR', 'indy'): 0x51,
    ('EOR', 'zpx'): 0x55,
    ('LSR', 'zpx'): 0x56,
    ('CLI', 'imp'): 0x58,
    ('EOR', 'absy'): 0x59,
    ('EOR', 'absx'): 0x5D,
    ('LSR', 'absx'): 0x5E,
    ('RTS', 'imp'): 0x60,
    ('ADC', 'indx'): 0x61,
    ('ADC', 'zp'): 0x65,
    ('ROR', 'zp'): 0x66,
    ('PLA', 'imp'): 0x68,
    ('ADC', 'imm'): 0x69,
    ('ROR', 'acc'): 0x6A,
    ('JMP', 'ind'): 0x6C,
    ('ADC', 'abs'): 0x6D,
    ('ROR', 'abs'): 0x6E,
    ('BVS', 'rel'): 0x70,
    ('ADC', 'indy'): 0x71,
    ('ADC', 'zpx'): 0x75,
    ('ROR', 'zpx'): 0x76,
    ('SEI', 'imp'): 0x78,
    ('ADC', 'absy'): 0x79,
    ('ADC', 'absx'): 0x7D,
    ('ROR', 'absx'): 0x7E,
    ('STA', 'indx'): 0x81,
    ('STY', 'zp'): 0x84,
    ('STA', 'zp'): 0x85,
    ('STX', 'zp'): 0x86,
    ('DEY', 'imp'): 0x88,
    ('TXA', 'imp'): 0x8A,
    ('STY', 'abs'): 0x8C,
    ('STA', 'abs'): 0x8D,
    ('STX', 'abs'): 0x8E,
    ('BCC', 'rel'): 0x90,
    ('STA', 'indy'): 0x91,
    ('STY', 'zpx'): 0x94,
    ('STA', 'zpx'): 0x95,
    ('STX', 'zpy'): 0x96,
    ('TYA', 'imp'): 0x98,
    ('STA', 'absy'): 0x99,
    ('TXS', 'imp'): 0x9A,
    ('STA', 'absx'): 0x9D,
    ('LDY', 'imm'): 0xA0,
    ('LDA', 'indx'): 0xA1,
    ('LDX', 'imm'): 0xA2,
    ('LDY', 'zp'): 0xA4,
    ('LDA', 'zp'): 0xA5,
    ('LDX', 'zp'): 0xA6,
    ('TAY', 'imp'): 0xA8,
    ('LDA', 'imm'): 0xA9,
    ('TAX', 'imp'): 0xAA,
    ('LDY', 'abs'): 0xAC,
    ('LDA', 'abs'): 0xAD,
    ('LDX', 'abs'): 0xAE,
    ('BCS', 'rel'): 0xB0,
    ('LDA', 'indy'): 0xB1,
    ('LDY', 'zpx'): 0xB4,
    ('LDA', 'zpx'): 0xB5,
    ('LDX', 'zpy'): 0xB6,
    ('CLV', 'imp'): 0xB8,
    ('LDA', 'absy'): 0xB9,
    ('TSX', 'imp'): 0xBA,
    ('LDY', 'absx'): 0xBC,
    ('LDA', 'absx'): 0xBD,
    ('LDX', 'absy'): 0xBE,
    ('CPY', 'imm'): 0xC0,
    ('CMP', 'indx'): 0xC1,
    ('CPY', 'zp'): 0xC4,
    ('CMP', 'zp'): 0xC5,
    ('DEC', 'zp'): 0xC6,
    ('INY', 'imp'): 0xC8,
    ('CMP', 'imm'): 0xC9,
    ('DEX', 'imp'): 0xCA,
    ('CPY', 'abs'): 0xCC,
    ('CMP', 'abs'): 0xCD,
    ('DEC', 'abs'): 0xCE,
    ('BNE', 'rel'): 0xD0,
    ('CMP', 'indy'): 0xD1,
    ('CMP', 'zpx'): 0xD5,
    ('DEC', 'zpx'): 0xD6,
    ('CLD', 'imp'): 0xD8,
    ('CMP', 'absy'): 0xD9,
    ('CMP', 'absx'): 0xDD,
    ('DEC', 'absx'): 0xDE,
    ('CPX', 'imm'): 0xE0,
    ('SBC', 'indx'): 0xE1,
    ('CPX', 'zp'): 0xE4,
    ('SBC', 'zp'): 0xE5,
    ('INC', 'zp'): 0xE6,
    ('INX', 'imp'): 0xE8,
    ('SBC', 'imm'): 0xE9,
    ('NOP', 'imp'): 0xEA,
    ('CPX', 'abs'): 0xEC,
    ('SBC', 'abs'): 0xED,
    ('INC', 'abs'): 0xEE,
    ('BEQ', 'rel'): 0xF0,
    ('SBC', 'indy'): 0xF1,
    ('SBC', 'zpx'): 0xF5,
    ('INC', 'zpx'): 0xF6,
    ('SED', 'imp'): 0xF8,
    ('SBC', 'absy'): 0xF9,
    ('SBC', 'absx'): 0xFD,
    ('INC', 'absx'): 0xFE
}
MNEMS = {m for m, _ in OPS}
BRANCH = {'BPL', 'BMI', 'BVC', 'BVS', 'BCC', 'BCS', 'BNE', 'BEQ'}
SIZE = {'imp': 1, 'acc': 1, 'imm': 2, 'zp': 2, 'zpx': 2, 'zpy': 2, 'indx': 2, 'indy': 2, 'rel': 2, 'abs': 3, 'absx': 3, 'absy': 3, 'ind': 3}

def val(tok, labels, final):
    tok = tok.strip(); total = 0
    for sign, t in re.findall(r'([+-]?)\s*([^+-]+)', tok):
        t = t.strip()
        if t.startswith('$'): v = int(t[1:], 16)
        elif t in labels: v = labels[t]
        else:
            try: v = int(t, 0)
            except ValueError:
                if final: raise SystemExit(f"unknown symbol {t!r}")
                v = 0
        total += -v if sign == '-' else v
    return total

def is_literal(tok):
    t = tok.strip()
    return bool(re.fullmatch(r'\$[0-9A-Fa-f]+|0[xX][0-9A-Fa-f]+|0[bB][01]+|\d+', t))

def pick(m, operand, labels, final):
    """-> (mode, value). Chooses the addressing mode from the operand syntax."""
    o = operand.strip(); mode = None; force = None
    if not o: return ('acc' if (m, 'acc') in OPS and (m, 'imp') not in OPS else 'imp'), 0
    if o.upper() == 'A': return 'acc', 0
    if o.startswith('#'): return 'imm', val(o[1:], labels, final)
    mm = re.fullmatch(r'\((.+),\s*[Xx]\)', o)
    if mm: return 'indx', val(mm.group(1), labels, final)
    mm = re.fullmatch(r'\((.+)\)\s*,\s*[Yy]', o)
    if mm: return 'indy', val(mm.group(1), labels, final)
    mm = re.fullmatch(r'\((.+)\)', o)
    if mm: return 'ind', val(mm.group(1), labels, final)
    idx = ''
    mm = re.fullmatch(r'(.+),\s*([XxYy])', o)
    if mm: o, idx = mm.group(1).strip(), mm.group(2).lower()
    if o.startswith('zp:'): force, o = 'zp', o[3:]
    elif o.startswith('abs:'): force, o = 'abs', o[4:]
    v = val(o, labels, final)
    if m in BRANCH: return 'rel', v
    zp_ok = force == 'zp' or (force is None and is_literal(o) and 0 <= v < 256)
    base = 'zp' if zp_ok else 'abs'
    mode = base + idx
    if (m, mode) not in OPS and base == 'zp' and force is None: mode = 'abs' + idx     # e.g. LDA 5,Y has no zp,Y: use abs,Y
    return mode, v

def assemble(lines, final, labels):
    mem = {}; pc = 0
    def emit(*bs):
        nonlocal pc
        for b in bs:
            if pc in mem: raise SystemExit(f"overlap at {pc:#06x}")
            if not 0 <= pc <= 0xFFFF: raise SystemExit(f"address {pc:#x} out of range")
            mem[pc] = b & 0xFF; pc += 1
    for ln in lines:
        ln = ln.split(';')[0].strip()
        while True:
            mm = re.match(r'([A-Za-z_][A-Za-z_0-9]*):(.*)', ln)
            if not mm: break
            labels[mm.group(1)] = pc; ln = mm.group(2).strip()
        if not ln: continue
        op, _, rest = ln.partition(' '); opu = op.upper()
        if opu == '.ORG': pc = val(rest, labels, final); continue
        if opu == '.BYTE':
            for a in rest.split(','):
                v = val(a, labels, final)
                if not -128 <= v <= 255: raise SystemExit(f".byte {v} out of range")
                emit(v)
            continue
        if opu == '.WORD':
            for a in rest.split(','): v = val(a, labels, final); emit(v & 255, (v >> 8) & 255)
            continue
        if opu not in MNEMS: raise SystemExit(f"unknown mnemonic {op!r}")
        mode, v = pick(opu, rest, labels, final)
        if (opu, mode) not in OPS: raise SystemExit(f"{opu} has no {mode} mode (documented modes only)")
        code = OPS[(opu, mode)]
        if mode in ('imp', 'acc'): emit(code)
        elif mode == 'rel':
            off = v - (pc + 2)
            if final and not -128 <= off <= 127: raise SystemExit(f"branch to {v:#06x} from {pc:#06x} out of range ({off})")
            emit(code, off)
        elif SIZE[mode] == 2:
            if final and not (-128 <= v <= 255 if mode == 'imm' else 0 <= v <= 255): raise SystemExit(f"{opu} operand {v} out of range for {mode}")
            emit(code, v)
        else:
            if final and not 0 <= v <= 0xFFFF: raise SystemExit(f"address {v:#x} out of range")
            emit(code, v & 255, v >> 8)
    return mem

def write_hex(mem, path):
    with open(path, 'w') as f:
        prev = None
        for a in sorted(mem):
            if prev is None or a != prev + 1: f.write(f"@{a:04X}\n")
            f.write(f"{mem[a]:02X}\n"); prev = a

def main():
    src, out = sys.argv[1], sys.argv[2]
    lines = open(src).read().splitlines(); labels = {}
    assemble(lines, False, labels)
    write_hex(assemble(lines, True, labels), out)

if __name__ == '__main__': main()
