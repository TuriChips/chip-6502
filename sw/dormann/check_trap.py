#!/usr/bin/env python3
"""Judges the log of a 6502 acceptance run (spec section 9 item 1). Homer.
Usage: check_trap.py functional <log>   Dormann's functional test: the run must end in the success trap at 3469h
       check_trap.py decimal <log> <spin_addr>   Clark's decimal test as built by build_decimal.py: the run must trap at the end-of-test spin
                                        (<spin_addr>, hex, from decimal.labels) and its console must show ERROR as the character 0
The simulator driver prints one line when the program stops by itself:
    'TRAP pc=XXXX clocks=N'   (the same PC fetched twice in a row: a 'jmp *' loop, how Dormann's test reports pass or fail)
    for the decimal test the console line before them is '0' (ERROR = 0, every case passed) or '1'
and 'TIMEOUT clocks=N' if it hit the clock limit. Exit 0 only on a pass; a timeout, a trap anywhere else or a missing line fails."""
import re, sys
def fail(m): print("FAIL:", m); sys.exit(1)
mode, log = sys.argv[1], open(sys.argv[2], errors="replace").read()
if "TIMEOUT" in log: fail("the run hit its clock limit before the program stopped")
if mode == "functional":
    bc = re.findall(r"^bus_conflict seen (\d+) times", log, re.M)
    if not bc: fail("no 'bus_conflict seen' line: the driver's output is not what this checker expects")
    if int(bc[-1]) > 0: fail("bus_conflict was seen %s times: a pass with bus conflicts is not a pass (spec section 8, C7)" % bc[-1])
    m = re.findall(r"^TRAP pc=([0-9A-Fa-f]{4}) clocks=(\d+)", log, re.M)
    if not m: fail("no TRAP line: the program never trapped")
    pc, clocks = m[-1]
    if pc.upper() != "3469": fail("trapped at %s, not at the success trap 3469 (a trap anywhere else is a failed check)" % pc.upper())
    print("PASS: Dormann functional test reached the success trap 3469 after %s clocks" % clocks)
elif mode == "decimal":
    if len(sys.argv) < 4: sys.exit("decimal mode needs the spin address of the built test: check_trap.py decimal <log> <spin_addr> (build_decimal.py writes it to decimal.labels)")
    spin = int(sys.argv[3], 16)
    bc = re.findall(r"^bus_conflict seen (\d+) times", log, re.M)
    if not bc: fail("no 'bus_conflict seen' line: the driver's output is not what this checker expects")
    if int(bc[-1]) > 0: fail("bus_conflict was seen %s times" % bc[-1])
    m = re.findall(r"^TRAP pc=([0-9A-Fa-f]{4}) clocks=(\d+)", log, re.M)
    if not m: fail("no TRAP line: the decimal test never reached its end")
    pc, clocks = m[-1]
    if int(pc, 16) != spin: fail("stopped at %s, not at the end-of-test spin %04X: stopping early is not a pass" % (pc.upper(), spin))
    # the console shows ERROR as one character: '0' (every case passed) or '1' (a case failed), on the line before the driver's own lines
    lines = log.splitlines()
    idx = next(i for i, l in enumerate(lines) if l.startswith("bus_conflict seen"))
    shown = lines[idx - 1].strip() if idx > 0 else ""
    if shown != "0": fail("decimal test printed ERROR = %r (0 is a pass)" % shown)
    print("PASS: Clark decimal test ran to its end (spin at %04X) with ERROR = 0 after %s clocks" % (spin, clocks))
else: sys.exit("mode must be functional or decimal")
