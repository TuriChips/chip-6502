#!/usr/bin/env python3
"""Judges the log of a 6502 acceptance run (spec section 9 item 1). Homer.
Usage: check_trap.py functional <log>   Dormann's functional test: the run must end in the success trap at 3469h
       check_trap.py decimal <log> <done_addr>   Clark's decimal test: the run must stop AT its DONE label (<done_addr>, hex, taken from the listing of
                                        the assembled test) with its ERROR byte (zero page 0Bh, the 12th entry of its bss) = 00
The simulator driver prints one line when the program stops by itself:
    'TRAP pc=XXXX clocks=N'   (the same PC fetched twice in a row: a 'jmp *' loop, how Dormann's test reports pass or fail)
    'STOP pc=XXXX clocks=N error=XX'   (the decimal test ended on its final instruction; error = the byte at 000Bh)
and 'TIMEOUT clocks=N' if it hit the clock limit. Exit 0 only on a pass; a timeout, a trap anywhere else or a missing line fails."""
import re, sys
def fail(m): print("FAIL:", m); sys.exit(1)
mode, log = sys.argv[1], open(sys.argv[2], errors="replace").read()
if "TIMEOUT" in log: fail("the run hit its clock limit before the program stopped")
if mode == "functional":
    m = re.findall(r"^TRAP pc=([0-9A-Fa-f]{4}) clocks=(\d+)", log, re.M)
    if not m: fail("no TRAP line: the program never trapped")
    pc, clocks = m[-1]
    if pc.upper() != "3469": fail("trapped at %s, not at the success trap 3469 (a trap anywhere else is a failed check)" % pc.upper())
    print("PASS: Dormann functional test reached the success trap 3469 after %s clocks" % clocks)
elif mode == "decimal":
    m = re.findall(r"^STOP pc=([0-9A-Fa-f]{4}) clocks=(\d+) error=([0-9A-Fa-f]{2})", log, re.M)
    if not m: fail("no STOP line: the decimal test never reached its end")
    pc, clocks, err = m[-1]
    if len(sys.argv) < 4: sys.exit("decimal mode needs the DONE label's address from the assembled listing: check_trap.py decimal <log> <done_addr>")
    if pc.upper() != "%04X" % int(sys.argv[3], 16):
        fail("stopped at %s, not at the DONE label %04X: stopping early with ERROR still 00 is not a pass" % (pc.upper(), int(sys.argv[3], 16)))
    if err.upper() != "00": fail("decimal test ended with ERROR = %s (00 is a pass)" % err.upper())
    print("PASS: Clark decimal test ended with ERROR = 00 after %s clocks" % clocks)
else: sys.exit("mode must be functional or decimal")
