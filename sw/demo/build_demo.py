#!/usr/bin/env python3
"""Builds the 6502 demo image by hand-assembling a small program (Homer, our own code). Usage: build_demo.py out.hex
The program prints "FIB" and the first 13 Fibonacci numbers in hex through the console port (a write to F001h), then spins in a
'jmp *' loop. Every instruction is listed with its address, bytes and meaning, so the encoding can be checked against the MOS opcode map
(docs/spec.md section 6.0). Expected console output: sw/demo/expected.txt."""
import sys
prog = {}
def put(addr, *b):
    for i, x in enumerate(b): prog[addr + i] = x
# 0200 main
put(0x0200, 0xA2, 0xFF)              # LDX #$FF
put(0x0202, 0x9A)                    # TXS
put(0x0203, 0xD8)                    # CLD
put(0x0204, 0xA0, 0x00)              # LDY #0
put(0x0206, 0xB9, 0x60, 0x02)        # msg: LDA $0260,Y
put(0x0209, 0xF0, 0x06)              # BEQ fib (0211)
put(0x020B, 0x8D, 0x01, 0xF0)        # STA $F001   (console)
put(0x020E, 0xC8)                    # INY
put(0x020F, 0xD0, 0xF5)              # BNE msg (0206)
put(0x0211, 0xA9, 0x01)              # fib: LDA #1
put(0x0213, 0x85, 0x10)              # STA $10   (a = 1)
put(0x0215, 0x85, 0x11)              # STA $11   (b = 1)
put(0x0217, 0xA2, 0x0D)              # LDX #13   (how many numbers)
put(0x0219, 0xA9, 0x20)              # loop: LDA #' '
put(0x021B, 0x8D, 0x01, 0xF0)        # STA $F001
put(0x021E, 0xA5, 0x10)              # LDA $10
put(0x0220, 0x20, 0x40, 0x02)        # JSR phex
put(0x0223, 0xA5, 0x10)              # LDA $10
put(0x0225, 0x18)                    # CLC
put(0x0226, 0x65, 0x11)              # ADC $11   (a + b)
put(0x0228, 0xA8)                    # TAY       (t = a + b)
put(0x0229, 0xA5, 0x11)              # LDA $11
put(0x022B, 0x85, 0x10)              # STA $10   (a = b)
put(0x022D, 0x84, 0x11)              # STY $11   (b = t)
put(0x022F, 0xCA)                    # DEX
put(0x0230, 0xD0, 0xE7)              # BNE loop (0219)
put(0x0232, 0xA9, 0x0A)              # LDA #10  (newline)
put(0x0234, 0x8D, 0x01, 0xF0)        # STA $F001
put(0x0237, 0x4C, 0x37, 0x02)        # JMP $0237  (spin: the driver stops here)
# 0240 phex: print A as two hex digits
put(0x0240, 0x48)                    # PHA
put(0x0241, 0x4A, 0x4A, 0x4A, 0x4A)  # LSR A x4 (high nibble)
put(0x0245, 0x20, 0x49, 0x02)        # JSR pnib
put(0x0248, 0x68)                    # PLA
put(0x0249, 0x29, 0x0F)              # pnib: AND #$0F
put(0x024B, 0xC9, 0x0A)              # CMP #10
put(0x024D, 0x90, 0x02)              # BCC +2 (to 0251)
put(0x024F, 0x69, 0x06)              # ADC #6   (carry is set: adds 7, so 10 becomes 'A')
put(0x0251, 0x69, 0x30)              # ADC #$30 (carry is clear here on both paths)
put(0x0253, 0x8D, 0x01, 0xF0)        # STA $F001
put(0x0256, 0x60)                    # RTS
put(0x0260, 0x46, 0x49, 0x42, 0x00)  # "FIB", 0
put(0xFFFC, 0x00, 0x02)              # reset vector -> 0200
open(sys.argv[1], "w").write("".join("@%04X %02X\n" % (a, prog[a]) for a in sorted(prog)))
