#!/usr/bin/env python3
"""Cross-check of two independent models written from the spec: mine (tests/mach6502.py) and Beru's (ref/ref6502.py): random programs of documented instructions on random
state and memory, compared instruction by instruction (every cycle's address, rw, data, sync, and A X Y S P PC after). Usage: crosscheck_ref.py <refdir> [instructions] [seed]"""
import os, random, sys
sys.dont_write_bytecode = True
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import asm6502 as A, mach6502 as M
ref = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 200000; seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
sys.path.insert(0, ref); import ref6502
rnd = random.Random(seed); codes = sorted(A.OPS.values()); bad = 0; shown = 0
for k in range(n):
    mem = {}; ramfn = lambda a: mem.get(a & 0xFFFF, 0)
    # random page-aligned neighbourhood so page crossings, wraps and the stack all occur
    pc = rnd.choice([rnd.randrange(0, 0x10000), 0x10F0 + rnd.randrange(16), 0x00F0 + rnd.randrange(16), 0xFFF0 + rnd.randrange(16)])
    for a in range(pc, pc + 4): mem[a & 0xFFFF] = rnd.randrange(256)
    mem[pc & 0xFFFF] = rnd.choice(codes)
    for a in list(range(0, 0x20)) + list(range(0x100, 0x200, 7)) + [rnd.randrange(65536) for _ in range(40)]: mem.setdefault(a, rnd.randrange(256))
    st = dict(a=rnd.randrange(256), x=rnd.randrange(256), y=rnd.randrange(256), s=rnd.randrange(256), p=rnd.randrange(256))
    mem2 = dict(mem)
    m = M.Mach(pc); m.mem = mem; m.a, m.x, m.y, m.s = st['a'], st['x'], st['y'], st['s']; m.setp(st['p'])
    c = ref6502.CPU(lambda a: mem2.get(a & 0xFFFF, 0), lambda a, v: mem2.__setitem__(a & 0xFFFF, v & 255)); c.pc = pc & 0xFFFF
    c.a, c.x, c.y, c.s = st['a'], st['x'], st['y'], st['s']; c.set_p(st['p'])
    mine = m.step(); theirs = c.step()
    ok = [tuple(x) for x in mine] == [tuple(x) for x in theirs] and (m.pc, m.s, m.a, m.x, m.y) == (c.pc, c.s, c.a, c.x, c.y) and (m.p(0) & 0xCF) == (c.p_byte(0) & 0xCF) and mem == mem2
    if not ok:
        bad += 1
        if shown < 5: shown += 1; print(f"differ: opcode {mem[pc & 0xFFFF]:02X} at {pc:04X}, state {st}: mine {mine} / ref {theirs}; mine pc,s,a,x,y,p {m.pc, m.s, m.a, m.x, m.y, m.p(0)} / ref {c.pc, c.s, c.a, c.x, c.y, c.p_byte(0)}")
print(f"{'PASS' if not bad else 'FAIL'} crosscheck_ref: {n} random instructions, {bad} differences")
sys.exit(1 if bad else 0)
