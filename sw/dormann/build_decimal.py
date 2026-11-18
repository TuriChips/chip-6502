#!/usr/bin/env python3
"""Builds Bruce Clark's 6502 decimal-mode test (public domain) for our CPU. Homer.
Usage: build_decimal.py 6502_decimal_test.a65 out.hex out.labels
The test is written for AS65 (macros, 'if', 'ds'). We translate it, line by line, into the syntax of tests/asm6502.py (Titus's assembler) and
assemble it there. Nothing in the test's logic is changed. What is set or replaced, all of it listed here:
  - options, as spec section 9 says: cputype = 0 (NMOS 6502), vld_bcd = 0 (invalid BCD allowed), chk_a = chk_n = chk_v = chk_z = chk_c = 1
    (the file's own defaults check only A and C; section 9 asks for all five)
  - 'if' / 'endif' blocks are evaluated with those options; 'bss' symbols ('ds') become zero page numbers from 0000h; 'org $200' is the code start
  - end_of_test: the file defines it as 'db $db', the 65C02 STP, which an NMOS 6502 does not have. We replace it with: LDA ERROR / ORA #$30 / STA $F001
    (print ERROR as the character '0' or '1' on the console) and a spin 'JMP *' at the label SPIN. ERROR is 0 only if every case passed
    (the test sets it to 1 first and to 0 only at its end); a failing case jumps to DONE with ERROR still 1.
out.labels gets 'NAME HEX' lines (SPIN, DONE, TEST) for the runner and the checker. The CPU starts at the reset vector; the runner sets FFFC/FFFD to TEST."""
import sys, re, os
sys.dont_write_bytecode = True
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "..", "tests"))
import asm6502

OPT = {"cputype": 0, "vld_bcd": 0, "chk_a": 1, "chk_n": 1, "chk_v": 1, "chk_z": 1, "chk_c": 1}
def num(t, sym):
    t = t.strip()
    if t.startswith("$"): return int(t[1:], 16)
    if re.fullmatch(r"\d+", t): return int(t)
    if t in sym: return sym[t]
    raise SystemExit("cannot evaluate %r" % t)
def expr(e, sym):
    total = 0
    for sign, t in re.findall(r"([+-]?)\s*([^+-]+)", e.strip()): total += (-1 if sign == "-" else 1) * num(t, sym)
    return total

src = open(sys.argv[1]).read().splitlines()
sym = dict(OPT)            # option symbols, then bss symbols
out = []
active = [True]            # nesting of 'if'
section = None; bss_addr = 0; in_macro = False
for raw in src:
    line = raw.split(";")[0].rstrip()
    if not line.strip(): continue
    label = None
    if not line[0].isspace():                       # a label (or a directive) starts in column 0
        m = re.match(r"(\S+)\s*(.*)", line); first, rest = m.group(1), m.group(2)
        if rest.lower().startswith("ds "): label, body = first, rest.strip()   # 'NAME ds N' in the bss section
        elif first.lower() in ("end", "bss", "code", "org") or re.match(r"[A-Za-z_]\w*\s*=", line) or rest.lower().startswith("macro") \
           or first.lower() in ("end_of_test",):
            body = line.strip()
        else: label, body = first, rest.strip()
    else: body = line.strip()
    low = body.lower()
    m = re.match(r"if\s+(\w+)\s*(=|!=)\s*(\d+)$", low)
    if m:
        v = sym[m.group(1)] if m.group(1) in sym else sym[next(k for k in sym if k.lower() == m.group(1))]
        active.append(active[-1] and ((v == int(m.group(3))) if m.group(2) == "=" else (v != int(m.group(3))))); continue
    if low == "endif": active.pop(); continue
    if not active[-1]: continue
    if in_macro:
        if low == "endm": in_macro = False
        continue                                     # the macro body (db $db) is replaced, see end_of_test below
    if "macro" in low.split(): in_macro = True; continue
    m = re.match(r"([A-Za-z_]\w*)\s*=\s*(\S+)$", body)
    if m and m.group(1) not in OPT:
        raise SystemExit("unexpected assignment " + body)
    if m: continue                                   # option lines: overridden above
    if low == "bss": section = "bss"; continue
    if low == "code": section = "code"; continue
    m = re.match(r"org\s+(\S+)$", low)
    if m:
        if section == "bss": bss_addr = num(m.group(1), sym)
        else: out.append("    .org %d" % num(m.group(1), sym))
        continue
    m = re.match(r"ds\s+(\d+)$", low)
    if m:
        if section != "bss" or not label: raise SystemExit("ds outside bss: " + raw)
        sym[label] = bss_addr; bss_addr += int(m.group(1)); continue
    if low.startswith("end "): continue
    if label: out.append(label + ":")
    if not body: continue                            # a label on a line of its own
    if low == "end_of_test":
        out += ["    lda %d" % sym["ERROR"], "    ora #$30", "    sta $F001", "SPIN: jmp SPIN"]; continue
    # an instruction: replace bss symbols in the operand with their numbers (so the assembler picks zero page)
    mm = re.match(r"(\w+)\s*(.*)$", body)
    if not mm: raise SystemExit("cannot parse: %r (raw %r)" % (body, raw))
    op, operand = mm.group(1), mm.group(2).strip()
    def sub(t):
        return re.sub(r"[A-Za-z_]\w*", lambda w: str(sym[w.group(0)]) if w.group(0) in sym and w.group(0) not in OPT else w.group(0), t)
    operand = operand if operand.startswith("#") and not re.search(r"[A-Za-z_]", operand[1:].replace("$", "")) else sub(operand) if not operand.startswith("#") else operand
    out.append("    %s %s" % (op, operand) if operand else "    " + op)
labels = {}
mem = asm6502.assemble(out, False, labels)
mem = asm6502.assemble(out, True, labels)
asm6502.write_hex(mem, sys.argv[2])
open(sys.argv[3], "w").write("".join("%s %04X\n" % (k, labels[k]) for k in ("TEST", "DONE", "SPIN")))
print("built %d bytes, TEST=%04X DONE=%04X SPIN=%04X" % (len(mem), labels["TEST"], labels["DONE"], labels["SPIN"]))
