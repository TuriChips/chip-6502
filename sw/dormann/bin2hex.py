#!/usr/bin/env python3
"""6502_functional_test.bin (64 KiB, loaded at 0000h) -> $readmemh image for m6502_mem. Usage: bin2hex.py in.bin out.hex
The only change to the binary: the reset vector (FFFCh/FFFDh) is set to 0400h. The pinned binary's vector points at its own
'res_trap'; Dormann's test is meant to be started at 0400h (the listing's start address), and our CPU starts from the reset vector.
Everything else, including the NMI and IRQ vector traps, is the pinned file, unmodified."""
import sys
b = bytearray(open(sys.argv[1], "rb").read())
if len(b) != 65536: sys.exit("expected a 64 KiB image, got %d bytes" % len(b))
b[0xFFFC], b[0xFFFD] = 0x00, 0x04
open(sys.argv[2], "w").write("".join("%02X\n" % x for x in b))
