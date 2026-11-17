# Coverage: spec behaviour -> test (MOS 6502)

Spec: docs/spec.md (v1). Status per row: **done** (test written and passing, log cited), **partial**, **todo**. Nothing is "passing" until a log in `logs/` says so. The RTL is not on main yet.

## §6.1 instructions (C1, C2; one row per mnemonic, all its modes)

| Mnemonic | Operation | Modes (opcode, cycles) | Test | Status |
|---|---|---|---|---|
| ADC | A + M + C → A, C | # 69 2 · zp 65 3 · zp,X 75 4 · abs 6D 4 · abs,X 7D 4+p · abs,Y 79 4+p · (zp,X) 61 6 · (zp),Y 71 5+p | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| AND | A ∧ M → A | # 29 2 · zp 25 3 · zp,X 35 4 · abs 2D 4 · abs,X 3D 4+p · abs,Y 39 4+p · (zp,X) 21 6 · (zp),Y 31 5+p (B-3 prints "5" without the asterisk; A.2.7 gives 6 on a page cross, so A governs) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| ASL | C ← [7…0] ← 0 | A 0A 2 · zp 06 5 · zp,X 16 6 · abs 0E 6 · abs,X 1E 7 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| BCC | branch if C = 0 | rel 90 2 (+1 taken, +2 taken to another page) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| BCS | branch if C = 1 | rel B0 2 (+1 / +2) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| BEQ | branch if Z = 1 | rel F0 2 (+1 / +2) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| BIT | A ∧ M; Z ← (A ∧ M = 0); **N ← M7, V ← M6** | zp 24 3 · abs 2C 4 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| BMI | branch if N = 1 | rel 30 2 (+1 / +2) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| BNE | branch if Z = 0 | rel D0 2 (+1 / +2) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| BPL | branch if N = 0 | rel 10 2 (+1 / +2) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| BRK | forced interrupt: PC + 2 ↓, P ↓, PC ← (FFFE) | impl 00 7. "A BRK command cannot be masked by setting I" (B-8) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| BVC | branch if V = 0 | rel 50 2 (+1 / +2) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| BVS | branch if V = 1 | rel 70 2 (+1 / +2) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| CLC | 0 → C | impl 18 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| CLD | 0 → D | impl D8 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| CLI | 0 → I | impl 58 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| CLV | 0 → V | impl B8 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| CMP | A − M (flags only) | # C9 2 · zp C5 3 · zp,X D5 4 · abs CD 4 · abs,X DD 4+p · abs,Y D9 4+p · (zp,X) C1 6 · (zp),Y D1 5+p | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| CPX | X − M (flags only) | # E0 2 · zp E4 3 · abs EC 4 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| CPY | Y − M (flags only) | # C0 2 · zp C4 3 · abs CC 4 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| DEC | M − 1 → M | zp C6 5 · zp,X D6 6 · abs CE 6 · abs,X DE 7 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| DEX | X − 1 → X | impl CA 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| DEY | Y − 1 → Y | impl 88 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| EOR | A ⊻ M → A | # 49 2 · zp 45 3 · zp,X 55 4 · abs 4D 4 · abs,X 5D 4+p · abs,Y 59 4+p · (zp,X) 41 6 · (zp),Y 51 5+p | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| INC | M + 1 → M | zp E6 5 · zp,X F6 6 · abs EE 6 · abs,X FE 7 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| INX | X + 1 → X | impl E8 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| INY | Y + 1 → Y | impl C8 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| JMP | (PC+1) → PCL, (PC+2) → PCH | abs 4C 3 · (abs) 6C 5 (page wrap, §6) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| JSR | PC + 2 ↓, (PC+1) → PCL, (PC+2) → PCH | abs 20 6 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| LDA | M → A | # A9 2 · zp A5 3 · zp,X B5 4 · abs AD 4 · abs,X BD 4+p · abs,Y B9 4+p · (zp,X) A1 6 · (zp),Y B1 5+p | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| LDX | M → X | # A2 2 · zp A6 3 · **zp,Y** B6 4 · abs AE 4 · **abs,Y** BE 4+p | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| LDY | M → Y | # A0 2 · zp A4 3 · zp,X B4 4 · abs AC 4 · abs,X BC 4+p | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| LSR | 0 → [7…0] → C | A 4A 2 · zp 46 5 · zp,X 56 6 · abs 4E 6 · abs,X 5E 7 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| NOP | none | impl EA 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| ORA | A ∨ M → A | # 09 2 · zp 05 3 · zp,X 15 4 · abs 0D 4 · abs,X 1D 4+p · abs,Y 19 4+p · (zp,X) 01 6 · (zp),Y 11 5+p (B-20 prints "5" without the asterisk, as for AND; A governs) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| PHA | A ↓ | impl 48 3 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| PHP | P ↓ (B = 1 and bit 5 = 1 in the pushed byte, §6 *Decision*) | impl 08 3 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| PLA | A ↑ | impl 68 4 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| PLP | P ↑ | impl 28 4 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| ROL | C ← [7…0] ← C | A 2A 2 · zp 26 5 · zp,X 36 6 · abs 2E 6 · abs,X 3E 7 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| ROR | C → [7…0] → C | A 6A 2 · zp 66 5 · zp,X 76 6 · abs 6E 6 · abs,X 7E 7 (B-23 repeats "available … after June, 1976"; §1 revision decision) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| RTI | P ↑, PC ↑ | impl 40 6 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| RTS | PC ↑, PC + 1 → PC | impl 60 6 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| SBC | A − M − C̄ → A (C̄ = borrow) | # E9 2 · zp E5 3 · zp,X F5 4 · abs ED 4 · abs,X FD 4+p · abs,Y F9 4+p · (zp,X) E1 6 · (zp),Y F1 5+p | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| SEC | 1 → C | impl 38 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| SED | 1 → D | impl F8 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| SEI | 1 → I | impl 78 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| STA | A → M | zp 85 3 · zp,X 95 4 · abs 8D 4 · abs,X 9D 5 · abs,Y 99 5 · (zp,X) 81 6 · (zp),Y 91 6 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| STX | X → M | zp 86 3 · **zp,Y** 96 4 · abs 8E 4 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| STY | Y → M | zp 84 3 · zp,X 94 4 · abs 8C 4 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| TAX | A → X | impl AA 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| TAY | A → Y | impl A8 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| TSX | S → X | impl BA 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| TXA | X → A | impl 8A 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| TXS | X → S | impl 9A 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |
| TYA | Y → A | impl 98 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1) |

## §8 behaviours

| ID | Behaviour | Test | Status |
|---|---|---|---|
| C1 | Every documented opcode in every addressing mode: registers, memory and flags per §6 | random programs of all 151 opcodes in every mode with random registers, P (incl. D) and memory, every cycle compared on the pins; registers and flags are exposed by later instructions that store them (the programs STA/PHA/PHP at random); each opcode executed >= 17 times; all PASS on the RTL | partial (PASS; directed exposure of A/X/Y/P after every instruction not yet: a wrong flag is only seen when a later branch or store reveals it) |
| C2 | Pin timing per §4 for every addressing mode, incl. dummy cycles, page crossings and RMW double writes | `tests/gen_cycles6502.py` + `tb/tb_cyc6502.sv`: a, rw, sync, d_oe and the written data in every cycle of the three programs (random indexes: page crossings and zero-page wraps both occur) | done for instructions (PASS, logs/rtl-run1); interrupts and RESET sequences with C4/C6 |
| C3 | RDY: stops reads at any read cycle, ignored on writes | | todo |
| C4 | Interrupts: IRQ masked by I, NMI edge, BRK, B in the pushed P, the branch delay, NMI hijacking BRK | | todo |
| C5 | Decimal mode per §6: A, C and NMOS N/V/Z, all 256 x 256 operands and both carries | | todo |
| C6 | Reset sequence and vectors | | todo |
| C7 | No X/Z, no bus conflict, with mutants and the positive bus_conflict case | | todo |
| C8 | Random programs vs the reference model | Beru | n/a |

## Cross-check against SingleStepTests/65x02 (spec 9 item 2, a cross-check not ground truth)

`tests/sst_crosscheck.py` runs my machine model (`tests/mach6502.py`, written from spec 4.1/6.1) against all 151 documented opcode files, 10,000 tests each (cycle-by-cycle bus activity, final registers, P and RAM): **1,510,000 tests, 0 differences** with the taken-branch cycles as Igris decided in chip-6502#19/#21 (T2 = PC+2, page-cross T3 = the uncarried target; the model's default; `M6502_BRANCH_REAL=0` selects the earlier literal text, under which only the 8 branch opcodes differ). Decimal mode (ADC/SBC with D = 1, spec 6 Decision) agrees with the vectors on every operand they sample.

## Tools

- `tests/mach6502.py`: cycle-accurate model (all 151 opcodes, per-cycle addresses/data, decimal mode, JMP-indirect wrap, B bit) from spec 4.1/6.1; `tests/mach6502_selftest.py` checks all 151 cycle counts against spec 6.1's table (PASS).
- `tests/asm6502.py`: assembler with the 151 opcodes of §6.0; `tests/asm6502_selftest.py` checks its table against the spec file and that every (mnemonic, mode) assembles to its byte (PASS).
