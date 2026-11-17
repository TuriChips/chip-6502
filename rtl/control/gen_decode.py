#!/usr/bin/env python3
"""Generates rtl/control/m6502_decode.v: the opcode decode table of m6502_control (blocks.md section 2, spec 6.0/6.1).
Usage: python3 rtl/control/gen_decode.py [spec.md]
Builds each field from the opcode's encoding and the instruction's meaning (spec 6.1), then checks that the set of
documented opcodes it knows is exactly the 151 listed in docs/spec.md section 6.1 (parsed from the instruction table),
that every mode's cycle count matches the table, and writes the Verilog. Undocumented opcodes decode as ok = 0 (NOP)."""
import re, sys, os
root = os.path.dirname(os.path.abspath(__file__)) + "/../.."
specf = sys.argv[1] if len(sys.argv) > 1 else root + "/docs/spec.md"

# modes (m6502_decode `mode`)
IMP, IMM, ZP, ZPX, ZPY, ABS, ABX, ABY, INX, INY, REL, PHX, PLX, JSR, RTS, RTI, BRK, JMPA, JMPI = range(19)
R, W, RMW = 0, 1, 2                     # cls
# ALU op codes (blocks.md section 3, Ada)
ADC, SBC, AND, ORA, EOR, CMP, BIT, ASL, LSR, ROL, ROR, INC, DEC, LD, CLC, SEC, CLI, SEI, CLD, SED, CLV = \
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21

ops = {}      # opcode -> dict
def put(op, mode, cls, aop=0, asel=0, bsel=0, awe=0, fwe=0, xwe=0, ywe=0, src=0, name=""):
    assert op not in ops, hex(op)
    ops[op] = dict(mode=mode, cls=cls, aop=aop, asel=asel, bsel=bsel, awe=awe, fwe=fwe, xwe=xwe, ywe=ywe, src=src, name=name)

# group cc=01
G1 = {0: ("ORA", ORA), 1: ("AND", AND), 2: ("EOR", EOR), 3: ("ADC", ADC), 5: ("LDA", LD), 6: ("CMP", CMP), 7: ("SBC", SBC)}
M1 = {0: INX, 1: ZP, 2: IMM, 3: ABS, 4: INY, 5: ZPX, 6: ABY, 7: ABX}
for a, (nm, aop) in G1.items():
    for b, mode in M1.items():
        put(a << 5 | b << 2 | 1, mode, R, aop=aop, awe=int(aop != CMP), fwe=1, name=nm)
for b, mode in M1.items():                       # STA (not immediate)
    if b != 2: put(4 << 5 | b << 2 | 1, mode, W, src=0, name="STA")
# group cc=10
for a, nm, aop in ((0, "ASL", ASL), (1, "ROL", ROL), (2, "LSR", LSR), (3, "ROR", ROR)):
    put(a << 5 | 0x0A, IMP, R, aop=aop, bsel=5, awe=1, fwe=1, name=nm + " A")
    for b, mode in ((1, ZP), (3, ABS), (5, ZPX), (7, ABX)):
        put(a << 5 | b << 2 | 2, mode, RMW, aop=aop, fwe=1, name=nm)
for a, nm, aop in ((6, "DEC", DEC), (7, "INC", INC)):
    for b, mode in ((1, ZP), (3, ABS), (5, ZPX), (7, ABX)):
        put(a << 5 | b << 2 | 2, mode, RMW, aop=aop, fwe=1, name=nm)
for b, mode in ((1, ZP), (3, ABS), (5, ZPY)): put(4 << 5 | b << 2 | 2, mode, W, src=1, name="STX")
for b, mode in ((0, IMM), (1, ZP), (3, ABS), (5, ZPY), (7, ABY)): put(5 << 5 | b << 2 | 2, mode, R, aop=LD, xwe=1, fwe=1, name="LDX")
# group cc=00
for b, mode in ((1, ZP), (3, ABS)): put(1 << 5 | b << 2, mode, R, aop=BIT, fwe=1, name="BIT")
for b, mode in ((1, ZP), (3, ABS), (5, ZPX)): put(4 << 5 | b << 2, mode, W, src=2, name="STY")
for b, mode in ((0, IMM), (1, ZP), (3, ABS), (5, ZPX), (7, ABX)): put(5 << 5 | b << 2, mode, R, aop=LD, ywe=1, fwe=1, name="LDY")
for b, mode in ((0, IMM), (1, ZP), (3, ABS)):
    put(6 << 5 | b << 2, mode, R, aop=CMP, asel=2, fwe=1, name="CPY")
    put(7 << 5 | b << 2, mode, R, aop=CMP, asel=1, fwe=1, name="CPX")
put(0x4C, JMPA, R, name="JMP"); put(0x6C, JMPI, R, name="JMP ind")
# branches
for op, nm in ((0x10, "BPL"), (0x30, "BMI"), (0x50, "BVC"), (0x70, "BVS"), (0x90, "BCC"), (0xB0, "BCS"), (0xD0, "BNE"), (0xF0, "BEQ")):
    put(op, REL, R, name=nm)
# implied, stack, control
for op, aop, nm in ((0x18, CLC, "CLC"), (0x38, SEC, "SEC"), (0x58, CLI, "CLI"), (0x78, SEI, "SEI"), (0xB8, CLV, "CLV"), (0xD8, CLD, "CLD"), (0xF8, SED, "SED")):
    put(op, IMP, R, aop=aop, fwe=1, name=nm)
put(0xEA, IMP, R, name="NOP")
put(0xAA, IMP, R, aop=LD, bsel=5, xwe=1, fwe=1, name="TAX"); put(0xA8, IMP, R, aop=LD, bsel=5, ywe=1, fwe=1, name="TAY")
put(0x8A, IMP, R, aop=LD, bsel=2, awe=1, fwe=1, name="TXA"); put(0x98, IMP, R, aop=LD, bsel=3, awe=1, fwe=1, name="TYA")
put(0xBA, IMP, R, aop=LD, bsel=4, xwe=1, fwe=1, name="TSX"); put(0x9A, IMP, R, name="TXS")
put(0xE8, IMP, R, aop=INC, bsel=2, xwe=1, fwe=1, name="INX"); put(0xC8, IMP, R, aop=INC, bsel=3, ywe=1, fwe=1, name="INY")
put(0xCA, IMP, R, aop=DEC, bsel=2, xwe=1, fwe=1, name="DEX"); put(0x88, IMP, R, aop=DEC, bsel=3, ywe=1, fwe=1, name="DEY")
put(0x48, PHX, W, src=0, name="PHA"); put(0x08, PHX, W, src=3, name="PHP")
put(0x68, PLX, R, aop=LD, awe=1, fwe=1, name="PLA"); put(0x28, PLX, R, name="PLP")
put(0x20, JSR, R, name="JSR"); put(0x60, RTS, R, name="RTS"); put(0x40, RTI, R, name="RTI"); put(0x00, BRK, R, name="BRK")

# ---- check against the spec's instruction table (6.1): every "<mode> <hex> <cycles>" token
spec = open(specf).read()
a = spec.index("### 6.1 Instructions"); b = spec.index("All 56 instructions transcribed")
tokens = re.findall(r"(?:^|[ ·|])(?:#|zp,X|zp,Y|zp|abs,X|abs,Y|abs|\(abs\)|\(zp,X\)|\(zp\),Y|A|impl|rel)\s+([0-9A-F]{2})\s+(\d)", spec[a:b].replace("**", ""))
spec_ops = {int(h, 16): int(c) for h, c in tokens}
assert len(spec_ops) == 151, f"parsed {len(spec_ops)} opcodes from the spec table"
assert set(spec_ops) == set(ops), (sorted(set(spec_ops) - set(ops)), sorted(set(ops) - set(spec_ops)))
# cycle count per (mode, cls) for the check; +1 for page-cross reads is not counted (spec's "4+p" shows as 4)
def cycles(m, c):
    base = {IMP: 2, IMM: 2, ZP: 3, ZPX: 4, ZPY: 4, ABS: 4, ABX: 4, ABY: 4, INX: 6, INY: 5, REL: 2, PHX: 3, PLX: 4, JSR: 6,
            RTS: 6, RTI: 6, BRK: 7, JMPA: 3, JMPI: 5}[m]
    if c == W and m in (ABX, ABY): return 5
    if c == W and m == INY: return 6
    if c == RMW: return {ZP: 5, ZPX: 6, ABS: 6, ABX: 7}[m]
    if c == W and m in (ZP, ZPX, ZPY, ABS, INX): return base
    return base
for op, d in ops.items():
    assert cycles(d["mode"], d["cls"]) == spec_ops[op], f"{op:02X} {d['name']}: model {cycles(d['mode'], d['cls'])} spec {spec_ops[op]}"

# ---- Verilog
out = ["// m6502_decode: opcode decode table for m6502_control. GENERATED by rtl/control/gen_decode.py from the opcode",
       "// encoding and docs/spec.md 6.1 (151 documented opcodes; the script checks the set and every cycle count against",
       "// the spec's table). Do not edit by hand. `ok` = 0 for the 105 undocumented bytes (executed as a 2-cycle NOP, spec 6).",
       "// mode: 0 IMP 1 IMM 2 ZP 3 ZPX 4 ZPY 5 ABS 6 ABX 7 ABY 8 (zp,X) 9 (zp),Y 10 REL 11 PHA/PHP 12 PLA/PLP 13 JSR 14 RTS 15 RTI 16 BRK",
       "// 17 JMP abs 18 JMP ind.  cls: 0 read/execute, 1 store, 2 read-modify-write.  src (stores): 0 A 1 X 2 Y 3 P.",
       "// aop/asel/bsel/awe/fwe/xwe/ywe: the ALU operation done in the instruction's execute cycle (blocks.md 2, 3).",
       "module m6502_decode (",
       "    input  wire [7:0] ir,",
       "    output reg        ok,",
       "    output reg  [4:0] mode,",
       "    output reg  [1:0] cls,",
       "    output reg  [4:0] aop,",
       "    output reg  [1:0] asel,",
       "    output reg  [2:0] bsel,",
       "    output reg        awe, fwe, xwe, ywe,",
       "    output reg  [1:0] src",
       ");",
       "    always @(*) begin",
       "        ok = 1'b0; mode = 5'd0; cls = 2'd0; aop = 5'd0; asel = 2'd0; bsel = 3'd0;",
       "        awe = 1'b0; fwe = 1'b0; xwe = 1'b0; ywe = 1'b0; src = 2'd0;",
       "        case (ir)"]
for op in sorted(ops):
    d = ops[op]
    out.append(f"            8'h{op:02X}: begin ok = 1'b1; mode = 5'd{d['mode']}; cls = 2'd{d['cls']}; aop = 5'd{d['aop']}; asel = 2'd{d['asel']}; "
               f"bsel = 3'd{d['bsel']}; awe = 1'b{d['awe']}; fwe = 1'b{d['fwe']}; xwe = 1'b{d['xwe']}; ywe = 1'b{d['ywe']}; src = 2'd{d['src']}; end  // {d['name']}")
out += ["            default: ;", "        endcase", "    end", "endmodule", ""]
open(os.path.dirname(os.path.abspath(__file__)) + "/m6502_decode.v", "w").write("\n".join(out))
print(f"wrote m6502_decode.v: {len(ops)} opcodes, all match docs/spec.md 6.1")
