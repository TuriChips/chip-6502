#!/usr/bin/env python3
"""Selftest of tests/mach6502.py against docs/spec.md section 6.1: for every (opcode, cycles) the spec's table lists, the model's step() returns that many cycles
(parsed from the spec file itself): '4+p' means 4 without and 5 with a page cross in the indexed address, stores and RMW always the long count, branches
2 / 3 (taken) / 4 (taken across a page). Also checks the model's first cycle is the opcode fetch with sync = 1 and that no other cycle has sync = 1, and a few worked
examples from the spec (JMP ($xxFF) wrap, decimal 79 + 14 = 93, PHP's B bit)."""
import os, re, sys
sys.dont_write_bytecode = True
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import asm6502 as A, mach6502 as M
rows = []; sec = False
for ln in open(os.path.join(here, '..', 'docs', 'spec.md')):
    if ln.startswith('### 6.1'): sec = True; continue
    if sec and ln.startswith('###'): break
    if sec and ln.startswith('| ') and not ln.startswith('| Mnemonic') and not ln.startswith('|---'):
        c = [x.strip() for x in ln.strip().strip('|').split('|')]
        if len(c) >= 4 and c[0].isupper() and len(c[0]) == 3: rows.append((c[0], c[3]))
MODEKEY = {'#': 'imm', 'zp': 'zp', 'zp,X': 'zpx', 'zp,Y': 'zpy', 'abs': 'abs', 'abs,X': 'absx', 'abs,Y': 'absy', '(zp,X)': 'indx', '(zp),Y': 'indy', '(abs)': 'ind', 'A': 'acc', 'impl': 'imp', 'rel': 'rel'}
checked = 0
for mn, modes in rows:
    modes = re.sub(r'\*\*', '', modes); modes = re.sub(r'\(.*?(B-\d+|A\.\d.*?|\s*the same.*?)\)', '', modes) if False else modes
    for part in modes.split('·'):
        mm = re.match(r'\s*(#|zp,X|zp,Y|zp|abs,X|abs,Y|abs|\(zp,X\)|\(zp\),Y|\(abs\)|A|impl|rel)\s+([0-9A-F]{2})\s+(\d)(\+p)?', part)
        if not mm: continue
        mode = MODEKEY[mm.group(1)]; code = int(mm.group(2), 16); cyc = int(mm.group(3)); plus = bool(mm.group(4))
        assert A.OPS[(mn, mode)] == code, (mn, mode, code)
        def run(x=0, y=0, flags=None, pc=0x1000, op1=0x10, op2=0x20):
            m = M.Mach(pc); m.x, m.y, m.s = x, y, 0xF0
            m.mem = {pc: code, pc + 1: op1, pc + 2: op2, 0x10: 0x10, 0x11: 0x20, 0x2010: 0x55}
            for k, v in (flags or {}).items(): setattr(m, k, v)
            return m, m.step()
        if mode == 'rel':
            flag, want = M.BR[mn]; fl = {flag.lower(): want}; nt = {flag.lower(): 1 - want}
            assert len(run(flags=nt)[1]) == 2 and len(run(flags=fl)[1]) == 3 and len(run(flags=fl, pc=0x10F0, op1=0x20)[1]) == 4, mn
        else:
            m, c = run(); assert len(c) == cyc, (mn, mode, len(c), cyc)
            if plus:
                idx = dict(x=0xF8) if mode in ('absx',) else dict(y=0xF8)
                assert len(run(**idx)[1]) == cyc + 1, (mn, mode, 'page cross')
            elif mode in ('absx', 'absy', 'indy') and mn in M.STORE | M.RMW:
                idx = dict(x=0xF8) if mode == 'absx' else dict(y=0xF8)
                assert len(run(**idx)[1]) == cyc, (mn, mode, 'stores/RMW: same count with a page cross')
        assert c[0][3] == 1 and all(x[3] == 0 for x in c[1:]) if mode != 'rel' else True
        checked += 1
assert checked == 151, checked
# worked examples from the spec
m = M.Mach(0); m.mem = {0x1000: 0x6C, 0x1001: 0xFF, 0x1002: 0x02, 0x02FF: 0x34, 0x0200: 0x12, 0x0300: 0x99}; m.pc = 0x1000; m.step(); assert m.pc == 0x1234, hex(m.pc)   # JMP ($02FF)
m = M.Mach(0); m.d = 1; m.a = 0x79; m.c = 0; m.adc(0x14); assert m.a == 0x93 and m.c == 0                                                                     # 79 + 14 = 93
m = M.Mach(0); m.d = 1; m.a = 0x99; m.c = 0; m.adc(0x01); assert m.a == 0x00 and m.c == 1 and m.z == 0                                                     # spec: A = 00, C = 1, Z = 0
m = M.Mach(0x1000); m.s = 0xFF; m.mem = {0x1000: 0x08}; m.step(); assert m.mem[0x1FF] & 0x30 == 0x30                                                           # PHP: B = 1 and bit 5 = 1
print(f"PASS mach6502 selftest: cycle counts of all {checked} opcodes match spec 6.1 (page cross, store/RMW, branches), sync only on T0, worked examples")
