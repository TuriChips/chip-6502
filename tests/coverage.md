# Coverage: spec behaviour -> test (MOS 6502)

Spec: docs/spec.md (v1). Status per row: **done** (test written and passing, log cited), **partial**, **todo**. Nothing is "passing" until a log in `logs/` says so. The RTL is not on main yet.

## §6.1 instructions (C1, C2; one row per mnemonic, all its modes)

| Mnemonic | Operation | Modes (opcode, cycles) | Test | Status |
|---|---|---|---|---|
| ADC | A + M + C → A, C | # 69 2 · zp 65 3 · zp,X 75 4 · abs 6D 4 · abs,X 7D 4+p · abs,Y 79 4+p · (zp,X) 61 6 · (zp),Y 71 5+p | | todo |
| AND | A ∧ M → A | # 29 2 · zp 25 3 · zp,X 35 4 · abs 2D 4 · abs,X 3D 4+p · abs,Y 39 4+p · (zp,X) 21 6 · (zp),Y 31 5+p (B-3 prints "5" without the asterisk; A.2.7 gives 6 on a page cross, so A governs) | | todo |
| ASL | C ← [7…0] ← 0 | A 0A 2 · zp 06 5 · zp,X 16 6 · abs 0E 6 · abs,X 1E 7 | | todo |
| BCC | branch if C = 0 | rel 90 2 (+1 taken, +2 taken to another page) | | todo |
| BCS | branch if C = 1 | rel B0 2 (+1 / +2) | | todo |
| BEQ | branch if Z = 1 | rel F0 2 (+1 / +2) | | todo |
| BIT | A ∧ M; Z ← (A ∧ M = 0); **N ← M7, V ← M6** | zp 24 3 · abs 2C 4 | | todo |
| BMI | branch if N = 1 | rel 30 2 (+1 / +2) | | todo |
| BNE | branch if Z = 0 | rel D0 2 (+1 / +2) | | todo |
| BPL | branch if N = 0 | rel 10 2 (+1 / +2) | | todo |
| BRK | forced interrupt: PC + 2 ↓, P ↓, PC ← (FFFE) | impl 00 7. "A BRK command cannot be masked by setting I" (B-8) | | todo |
| BVC | branch if V = 0 | rel 50 2 (+1 / +2) | | todo |
| BVS | branch if V = 1 | rel 70 2 (+1 / +2) | | todo |
| CLC | 0 → C | impl 18 2 | | todo |
| CLD | 0 → D | impl D8 2 | | todo |
| CLI | 0 → I | impl 58 2 | | todo |
| CLV | 0 → V | impl B8 2 | | todo |
| CMP | A − M (flags only) | # C9 2 · zp C5 3 · zp,X D5 4 · abs CD 4 · abs,X DD 4+p · abs,Y D9 4+p · (zp,X) C1 6 · (zp),Y D1 5+p | | todo |
| CPX | X − M (flags only) | # E0 2 · zp E4 3 · abs EC 4 | | todo |
| CPY | Y − M (flags only) | # C0 2 · zp C4 3 · abs CC 4 | | todo |
| DEC | M − 1 → M | zp C6 5 · zp,X D6 6 · abs CE 6 · abs,X DE 7 | | todo |
| DEX | X − 1 → X | impl CA 2 | | todo |
| DEY | Y − 1 → Y | impl 88 2 | | todo |
| EOR | A ⊻ M → A | # 49 2 · zp 45 3 · zp,X 55 4 · abs 4D 4 · abs,X 5D 4+p · abs,Y 59 4+p · (zp,X) 41 6 · (zp),Y 51 5+p | | todo |
| INC | M + 1 → M | zp E6 5 · zp,X F6 6 · abs EE 6 · abs,X FE 7 | | todo |
| INX | X + 1 → X | impl E8 2 | | todo |
| INY | Y + 1 → Y | impl C8 2 | | todo |
| JMP | (PC+1) → PCL, (PC+2) → PCH | abs 4C 3 · (abs) 6C 5 (page wrap, §6) | | todo |
| JSR | PC + 2 ↓, (PC+1) → PCL, (PC+2) → PCH | abs 20 6 | | todo |
| LDA | M → A | # A9 2 · zp A5 3 · zp,X B5 4 · abs AD 4 · abs,X BD 4+p · abs,Y B9 4+p · (zp,X) A1 6 · (zp),Y B1 5+p | | todo |
| LDX | M → X | # A2 2 · zp A6 3 · **zp,Y** B6 4 · abs AE 4 · **abs,Y** BE 4+p | | todo |
| LDY | M → Y | # A0 2 · zp A4 3 · zp,X B4 4 · abs AC 4 · abs,X BC 4+p | | todo |
| LSR | 0 → [7…0] → C | A 4A 2 · zp 46 5 · zp,X 56 6 · abs 4E 6 · abs,X 5E 7 | | todo |
| NOP | none | impl EA 2 | | todo |
| ORA | A ∨ M → A | # 09 2 · zp 05 3 · zp,X 15 4 · abs 0D 4 · abs,X 1D 4+p · abs,Y 19 4+p · (zp,X) 01 6 · (zp),Y 11 5+p (B-20 prints "5" without the asterisk, as for AND; A governs) | | todo |
| PHA | A ↓ | impl 48 3 | | todo |
| PHP | P ↓ (B = 1 and bit 5 = 1 in the pushed byte, §6 *Decision*) | impl 08 3 | | todo |
| PLA | A ↑ | impl 68 4 | | todo |
| PLP | P ↑ | impl 28 4 | | todo |
| ROL | C ← [7…0] ← C | A 2A 2 · zp 26 5 · zp,X 36 6 · abs 2E 6 · abs,X 3E 7 | | todo |
| ROR | C → [7…0] → C | A 6A 2 · zp 66 5 · zp,X 76 6 · abs 6E 6 · abs,X 7E 7 (B-23 repeats "available … after June, 1976"; §1 revision decision) | | todo |
| RTI | P ↑, PC ↑ | impl 40 6 | | todo |
| RTS | PC ↑, PC + 1 → PC | impl 60 6 | | todo |
| SBC | A − M − C̄ → A (C̄ = borrow) | # E9 2 · zp E5 3 · zp,X F5 4 · abs ED 4 · abs,X FD 4+p · abs,Y F9 4+p · (zp,X) E1 6 · (zp),Y F1 5+p | | todo |
| SEC | 1 → C | impl 38 2 | | todo |
| SED | 1 → D | impl F8 2 | | todo |
| SEI | 1 → I | impl 78 2 | | todo |
| STA | A → M | zp 85 3 · zp,X 95 4 · abs 8D 4 · abs,X 9D 5 · abs,Y 99 5 · (zp,X) 81 6 · (zp),Y 91 6 | | todo |
| STX | X → M | zp 86 3 · **zp,Y** 96 4 · abs 8E 4 | | todo |
| STY | Y → M | zp 84 3 · zp,X 94 4 · abs 8C 4 | | todo |
| TAX | A → X | impl AA 2 | | todo |
| TAY | A → Y | impl A8 2 | | todo |
| TSX | S → X | impl BA 2 | | todo |
| TXA | X → A | impl 8A 2 | | todo |
| TXS | X → S | impl 9A 2 | | todo |
| TYA | Y → A | impl 98 2 | | todo |

## §8 behaviours

| ID | Behaviour | Test | Status |
|---|---|---|---|
| C1 | Every documented opcode in every addressing mode: registers, memory and flags per §6 | (the rows above) | todo |
| C2 | Pin timing per §4 for every addressing mode, incl. dummy cycles, page crossings and RMW double writes | | todo |
| C3 | RDY: stops reads at any read cycle, ignored on writes | | todo |
| C4 | Interrupts: IRQ masked by I, NMI edge, BRK, B in the pushed P, the branch delay, NMI hijacking BRK | | todo |
| C5 | Decimal mode per §6: A, C and NMOS N/V/Z, all 256 x 256 operands and both carries | | todo |
| C6 | Reset sequence and vectors | | todo |
| C7 | No X/Z, no bus conflict, with mutants and the positive bus_conflict case | | todo |
| C8 | Random programs vs the reference model | Beru | n/a |

## Cross-check against SingleStepTests/65x02 (spec 9 item 2, a cross-check not ground truth)

`tests/sst_crosscheck.py` runs my machine model (`tests/mach6502.py`, written from spec 4.1/6.1) against all 151 documented opcode files, 10,000 tests each (cycle-by-cycle bus activity, final registers, P and RAM): **1,510,000 tests, 0 differences** when the taken-branch cycles follow the vectors (`M6502_BRANCH_REAL=1`). With spec 4.1 A.5.8 as written, only the 8 branch opcodes differ (taken branches: the T2 address, and the carried vs uncarried T3 address): filed for Igris. Decimal mode (ADC/SBC with D = 1, spec 6 Decision) agrees with the vectors on every operand they sample.

## Tools

- `tests/mach6502.py`: cycle-accurate model (all 151 opcodes, per-cycle addresses/data, decimal mode, JMP-indirect wrap, B bit) from spec 4.1/6.1; `tests/mach6502_selftest.py` checks all 151 cycle counts against spec 6.1's table (PASS).
- `tests/asm6502.py`: assembler with the 151 opcodes of §6.0; `tests/asm6502_selftest.py` checks its table against the spec file and that every (mnemonic, mode) assembles to its byte (PASS).
