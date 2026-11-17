#!/usr/bin/env python3
"""Generates rtl/control/m6502_plan.v: the per-cycle plan of m6502_control (spec 4.1 / Appendix A, with the A.5.8
branch Decision of chip-6502#21), as a table keyed by (mode, class, T, ab_carry, branch taken, branch page-cross,
interrupt-sequence, NMI). Run after gen_decode.py (it imports it). The script also *walks* the plan for all 151
documented opcodes, with and without a page cross, and checks the number of cycles against docs/spec.md 6.1
(including 2/3/4 for branches). Usage: python3 rtl/control/gen_plan.py"""
import os, sys
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import gen_decode as D           # runs the decode generator and its spec checks
(IMP, IMM, ZP, ZPX, ZPY, ABS, ABX, ABY, INX, INY, REL, PHX, PLX, JSR, RTS, RTI, BRK, JMPA, JMPI) = range(19)
R, W, RMW = 0, 1, 2

FIELDS = [("addr", 3), ("vec", 3), ("ab", 4), ("pc", 2), ("s", 2), ("dout", 3), ("wr", 1), ("last", 1), ("ex", 1),
          ("tmpl", 1), ("tmpb", 1), ("dint", 1), ("pull", 1), ("pushb", 1), ("dsrc", 1), ("sei", 1)]
rows = []      # (key dict, field dict)

def cyc(addr, t, key, **f):
    d = dict(addr=addr, vec=0, ab=0, pc=0, s=0, dout=0, wr=0, last=0, ex=0, tmpl=0, tmpb=0, dint=0, pull=0,
             pushb=0, dsrc=0, sei=0)
    d.update(f); k = dict(mode=key[0], cls=key[1], t=t, car=None, tk=None, cr=None, isq=None, nmi=None)
    k.update(key[2] if len(key) > 2 else {})
    rows.append((k, d))

def seq(mode, cls, lst):
    # lst: list of (addr, kwargs, cond-dict or None)
    for t, (addr, kw, cond) in enumerate(lst, start=1):
        k = (mode, cls, cond or {})
        cyc(addr, t, k, **kw)

def fetch1(ab=1): return (0, dict(ab=ab, pc=1), None)

for mode, abx in ((ZPX, 3), (ZPY, 4)):
    seq(mode, R,   [fetch1(), (2, dict(ab=abx), None), (2, dict(ex=1, last=1), None)])
    seq(mode, W,   [fetch1(), (2, dict(ab=abx), None), (2, dict(wr=1, dsrc=1, last=1), None)])
seq(ZPX, RMW, [fetch1(), (2, dict(ab=3), None), (2, dict(tmpl=1), None), (2, dict(wr=1, dout=6), None),
               (2, dict(wr=1, dout=7, ex=1, tmpb=1, last=1), None)])
seq(ZP, R,   [fetch1(), (2, dict(ex=1, last=1), None)])
seq(ZP, W,   [fetch1(), (2, dict(wr=1, dsrc=1, last=1), None)])
seq(ZP, RMW, [fetch1(), (2, dict(tmpl=1), None), (2, dict(wr=1, dout=6), None), (2, dict(wr=1, dout=7, ex=1, tmpb=1, last=1), None)])
seq(IMM, R,  [(0, dict(pc=1, ex=1, last=1), None)])
seq(IMP, R,  [(0, dict(ex=1, last=1), None)])
seq(ABS, R,  [fetch1(), (0, dict(ab=2, pc=1), None), (1, dict(ex=1, last=1), None)])
seq(ABS, W,  [fetch1(), (0, dict(ab=2, pc=1), None), (1, dict(wr=1, dsrc=1, last=1), None)])
seq(ABS, RMW,[fetch1(), (0, dict(ab=2, pc=1), None), (1, dict(tmpl=1), None), (1, dict(wr=1, dout=6), None),
              (1, dict(wr=1, dout=7, ex=1, tmpb=1, last=1), None)])
for mode, abx in ((ABX, 14), (ABY, 15)):
    seq(mode, R, [fetch1(), (0, dict(ab=abx, pc=1), None), (1, dict(ex=1, last=1), dict(car=0))])
    cyc(1, 3, (mode, R, dict(car=1)), ab=5)
    cyc(1, 4, (mode, R, {}), ex=1, last=1)
    seq(mode, W, [fetch1(), (0, dict(ab=abx, pc=1), None), (1, dict(ab=5), None), (1, dict(wr=1, dsrc=1, last=1), None)])
seq(ABX, RMW, [fetch1(), (0, dict(ab=14, pc=1), None), (1, dict(ab=5), None), (1, dict(tmpl=1), None), (1, dict(wr=1, dout=6), None),
               (1, dict(wr=1, dout=7, ex=1, tmpb=1, last=1), None)])
seq(INX, R, [fetch1(), (2, dict(ab=3), None), (2, dict(ab=11), None), (2, dict(ab=12), None), (1, dict(ex=1, last=1), None)])
seq(INX, W, [fetch1(), (2, dict(ab=3), None), (2, dict(ab=11), None), (2, dict(ab=12), None), (1, dict(wr=1, dsrc=1, last=1), None)])
seq(INY, R, [fetch1(), (2, dict(ab=11), None), (2, dict(ab=13), None), (1, dict(ex=1, last=1), dict(car=0))])
cyc(1, 4, (INY, R, dict(car=1)), ab=5)
cyc(1, 5, (INY, R, {}), ex=1, last=1)
seq(INY, W, [fetch1(), (2, dict(ab=11), None), (2, dict(ab=13), None), (1, dict(ab=5), None), (1, dict(wr=1, dsrc=1, last=1), None)])
# branches (A.5.8 with the chip-6502#21 Decision): T1 offset (PC+1 -> PC+2), taken: T2 at PC+2 (offset added to PCL from TMP),
# page cross: T3 at the uncarried target (PCH fixed)
cyc(0, 1, (REL, R, dict(tk=0)), pc=1, tmpl=1, last=1)
cyc(0, 1, (REL, R, dict(tk=1)), pc=1, tmpl=1)
cyc(0, 2, (REL, R, dict(cr=0)), ab=9, dint=1, last=1)
cyc(0, 2, (REL, R, dict(cr=1)), ab=9, dint=1)
cyc(0, 3, (REL, R, {}), ab=10, last=1)
seq(PHX, W, [(0, {}, None), (3, dict(wr=1, dsrc=1, pushb=1, s=1, last=1), None)])
seq(PLX, R, [(0, {}, None), (3, dict(s=2), None), (3, dict(ex=1, pull=1, last=1), None)])
seq(JSR, R, [fetch1(), (3, {}, None), (3, dict(wr=1, dout=4, s=1), None), (3, dict(wr=1, dout=5, s=1), None), (0, dict(ab=7, last=1), None)])
seq(RTS, R, [(0, {}, None), (3, dict(s=2), None), (3, dict(pc=2, s=2), None), (3, dict(pc=3), None), (0, dict(pc=1, last=1), None)])
seq(RTI, R, [(0, {}, None), (3, dict(s=2), None), (3, dict(pull=1, s=2), None), (3, dict(pc=2, s=2), None), (3, dict(pc=3, last=1), None)])
for isq in (0, 1):
    for nmi in (0, 1):
        c = dict(isq=isq, nmi=nmi)
        pb = 0 if isq else 1
        seq(BRK, R, [(0, dict(pc=0 if isq else 1), c), (3, dict(wr=1, dout=4, s=1), c), (3, dict(wr=1, dout=5, s=1), c),
                     (3, dict(wr=1, dout=3, s=1, pushb=pb), c), (5, dict(vec=(0 if nmi else 4), ab=1), c),
                     (5, dict(vec=(1 if nmi else 5), ab=7, sei=1, last=1), c)])
seq(JMPA, R, [fetch1(), (0, dict(ab=7, last=1), None)])
seq(JMPI, R, [fetch1(), (0, dict(ab=2), None), (1, dict(pc=2, ab=6), None), (1, dict(pc=3, last=1), None)])

# ---- walk the plan: cycle counts per opcode vs the spec (via gen_decode's checked table)
def lookup(mode, cls, t, car, tk, cr, isq=0, nmi=0):
    hit = None
    for k, d in rows:
        if k["mode"] != mode or k["cls"] != cls or k["t"] != t: continue
        if any(k[n] is not None and k[n] != v for n, v in (("car", car), ("tk", tk), ("cr", cr), ("isq", isq), ("nmi", nmi))): continue
        assert hit is None, f"plan rows overlap: mode {mode} cls {cls} t {t}"
        hit = d
    return hit
def walk(mode, cls, car=0, tk=1, cr=0):
    n = 1                                   # T0
    for t in range(1, 8):
        d = lookup(mode, cls, t, car, tk, cr)
        assert d is not None, f"no plan row: mode {mode} cls {cls} t {t} car {car} tk {tk} cr {cr}"
        n += 1
        if d["last"]: return n
    raise AssertionError("never last")
spec_cycles = D.spec_ops
for op, d in D.ops.items():
    m, c = d["mode"], d["cls"]
    if m == REL:
        assert (walk(m, c, tk=0), walk(m, c, tk=1, cr=0), walk(m, c, tk=1, cr=1)) == (2, 3, 4), hex(op)
    elif m == BRK:
        assert walk(m, c) == 7
    else:
        base = walk(m, c, car=0)
        assert base == spec_cycles[op], f"{op:02X} {d['name']}: plan {base} spec {spec_cycles[op]}"
        if m in (ABX, ABY, INY) and c == R:
            assert walk(m, c, car=1) == spec_cycles[op] + 1, f"{op:02X} page-cross length"

# ---- Verilog
def pat(k):
    f = lambda v, w: ("?" * w) if v is None else format(v, f"0{w}b")
    return f"{{5'b{f(k['mode'],5)}, 2'b{f(k['cls'],2)}, 3'b{f(k['t'],3)}, 1'b{f(k['car'],1)}, 1'b{f(k['tk'],1)}, 1'b{f(k['cr'],1)}, 1'b{f(k['isq'],1)}, 1'b{f(k['nmi'],1)}}}"
tot = sum(w for _, w in FIELDS)
out = ["// m6502_plan: the per-cycle plan table of m6502_control. GENERATED by rtl/control/gen_plan.py (spec 4.1 / Appendix A, branch",
       "// timing per the chip-6502#21 Decision); the generator walks it for all 151 opcodes and checks the cycle counts against",
       "// docs/spec.md 6.1. Do not edit by hand.",
       "// addr: addr_sel; vec: vec_sel; ab: ab_op; pc: pc_op; s: s_op; dout: d_out_sel when dsrc = 0; wr: write cycle;",
       "// last: last cycle of the instruction; ex: do the instruction's ALU operation (decode fields); tmpl: latch TMP from d_in;",
       "// tmpb: ALU b = TMP; dint: regs' d_in = TMP; pull: P <- b (PLP, RTI); pushb: B = 1 in the pushed P; dsrc: d_out_sel from",
       "// the opcode's store source (A, X, Y, P); sei: set I (interrupt sequences).",
       "module m6502_plan (",
       "    input  wire [4:0] mode,", "    input  wire [1:0] cls,", "    input  wire [2:0] t,", "    input  wire       car, tk, cr, isq, nmi,"]
out += [f"    output reg  [{w-1}:0] {n}," if w > 1 else f"    output reg        {n}," for n, w in FIELDS]
out[-1] = out[-1].rstrip(",")
out += [");", "    always @(*) begin"]
out.append("        {" + ", ".join(n for n, _ in FIELDS) + "} = " + f"{tot}'d0;")
out.append("        casez ({mode, cls, t, car, tk, cr, isq, nmi})")
for k, d in rows:
    val = "{" + ", ".join(f"{w}'d{d[n]}" for n, w in FIELDS) + "}"
    out.append(f"            {pat(k)}: " + "{" + ", ".join(n for n, _ in FIELDS) + "} = " + val + ";")
out += ["            default: ;", "        endcase", "    end", "endmodule", ""]
open(here + "/m6502_plan.v", "w").write("\n".join(out))
print(f"wrote m6502_plan.v: {len(rows)} rows; cycle counts of all {len(D.ops)} opcodes match docs/spec.md 6.1")
