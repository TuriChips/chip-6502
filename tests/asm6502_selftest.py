#!/usr/bin/env python3
"""Checks tests/asm6502.py against docs/spec.md section 6.0 (the opcode map, parsed from the spec file itself): the assembler's table equals the
map, every documented (mnemonic, mode) assembles to exactly its byte with the right operand length, each of the 151 opcodes appears once, and
the 105 'Future Expansion' bytes are not producible. Run from the repo root."""
import os, re, sys
sys.dont_write_bytecode = True
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import asm6502 as A
MODES = {'#': 'imm', 'zp': 'zp', 'zp,X': 'zpx', 'zp,Y': 'zpy', 'abs': 'abs', 'abs,X': 'absx', 'abs,Y': 'absy', '(zp,X)': 'indx', '(zp),Y': 'indy', '(abs)': 'ind', 'A': 'acc', 'rel': 'rel'}
spec = {}; sec = False; rows = 0
for ln in open(os.path.join(here, '..', 'docs', 'spec.md')):
    if ln.startswith('### 6.0'): sec = True; continue
    if sec and ln.startswith('###'): break
    if sec and ln.startswith('| ') and not ln.startswith('| hi') and not ln.startswith('|---'):
        c = [x.strip() for x in ln.strip().strip('|').split('|')]; hi = rows; rows += 1
        for lo, cell in enumerate(c[1:]):
            if cell == '·': continue
            p = cell.split(' ', 1); spec[(p[0], MODES[p[1]] if len(p) > 1 else 'imp')] = hi * 16 + lo
assert rows == 16 and len(spec) == 151, (rows, len(spec))
assert spec == A.OPS, "assembler table differs from the spec's opcode map"
assert len(set(spec.values())) == 151
SRC = {'imp': '{m}', 'acc': '{m} A', 'imm': '{m} #$12', 'zp': '{m} $12', 'zpx': '{m} $12,X', 'zpy': '{m} $12,Y', 'abs': '{m} $1234', 'absx': '{m} $1234,X',
       'absy': '{m} $1234,Y', 'indx': '{m} ($12,X)', 'indy': '{m} ($12),Y', 'ind': '{m} ($1234)', 'rel': '{m} $0102'}
LEN = {'imp': 1, 'acc': 1, 'imm': 2, 'zp': 2, 'zpx': 2, 'zpy': 2, 'abs': 3, 'absx': 3, 'absy': 3, 'indx': 2, 'indy': 2, 'ind': 3, 'rel': 2}
for (m, mode), code in spec.items():
    mem = A.assemble(['.org $0100', SRC[mode].format(m=m)], True, {}); got = [mem[k] for k in sorted(mem)]
    assert got[0] == code and len(got) == LEN[mode], f"{m} {mode}: {got}, expected {code:02X}"
    if mode == 'rel': assert got[1] == (0x0102 - 0x0102) & 255, got      # target 0102 from 0100: offset 0
for bad in ("LDA", "STA #1", "JMP 5,X", "BNE $0300", "LDX 5,X", "ASL #1", "LDA #300", "FOO 1"):
    try: A.assemble(['.org 0', bad], True, {}); raise AssertionError(f"{bad!r} should be rejected")
    except SystemExit: pass
print("PASS asm6502 selftest: 151 documented opcodes match the spec's map, each assembles to its byte; 105 undocumented bytes not producible")
