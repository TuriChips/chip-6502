# Coverage: spec behaviour -> test (MOS 6502)

Spec: docs/spec.md (v1). Status per row: **done** (test written and passing, log cited), **partial**, **todo**. Nothing is "passing" until a log in `logs/` says so. The RTL is not on main yet.

## §6.1 instructions (C1, C2; one row per mnemonic, all its modes)

| Mnemonic | Operation | Modes (opcode, cycles) | Test | Status |
|---|---|---|---|---|
| ADC | A + M + C → A, C | # 69 2 · zp 65 3 · zp,X 75 4 · abs 6D 4 · abs,X 7D 4+p · abs,Y 79 4+p · (zp,X) 61 6 · (zp),Y 71 5+p | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| AND | A ∧ M → A | # 29 2 · zp 25 3 · zp,X 35 4 · abs 2D 4 · abs,X 3D 4+p · abs,Y 39 4+p · (zp,X) 21 6 · (zp),Y 31 5+p (B-3 prints "5" without the asterisk; A.2.7 gives 6 on a page cross, so A governs) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| ASL | C ← [7…0] ← 0 | A 0A 2 · zp 06 5 · zp,X 16 6 · abs 0E 6 · abs,X 1E 7 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| BCC | branch if C = 0 | rel 90 2 (+1 taken, +2 taken to another page) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| BCS | branch if C = 1 | rel B0 2 (+1 / +2) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| BEQ | branch if Z = 1 | rel F0 2 (+1 / +2) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| BIT | A ∧ M; Z ← (A ∧ M = 0); **N ← M7, V ← M6** | zp 24 3 · abs 2C 4 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| BMI | branch if N = 1 | rel 30 2 (+1 / +2) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| BNE | branch if Z = 0 | rel D0 2 (+1 / +2) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| BPL | branch if N = 0 | rel 10 2 (+1 / +2) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| BRK | forced interrupt: PC + 2 ↓, P ↓, PC ← (FFFE) | impl 00 7. "A BRK command cannot be masked by setting I" (B-8) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| BVC | branch if V = 0 | rel 50 2 (+1 / +2) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| BVS | branch if V = 1 | rel 70 2 (+1 / +2) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| CLC | 0 → C | impl 18 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| CLD | 0 → D | impl D8 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| CLI | 0 → I | impl 58 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| CLV | 0 → V | impl B8 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| CMP | A − M (flags only) | # C9 2 · zp C5 3 · zp,X D5 4 · abs CD 4 · abs,X DD 4+p · abs,Y D9 4+p · (zp,X) C1 6 · (zp),Y D1 5+p | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| CPX | X − M (flags only) | # E0 2 · zp E4 3 · abs EC 4 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| CPY | Y − M (flags only) | # C0 2 · zp C4 3 · abs CC 4 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| DEC | M − 1 → M | zp C6 5 · zp,X D6 6 · abs CE 6 · abs,X DE 7 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| DEX | X − 1 → X | impl CA 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| DEY | Y − 1 → Y | impl 88 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| EOR | A ⊻ M → A | # 49 2 · zp 45 3 · zp,X 55 4 · abs 4D 4 · abs,X 5D 4+p · abs,Y 59 4+p · (zp,X) 41 6 · (zp),Y 51 5+p | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| INC | M + 1 → M | zp E6 5 · zp,X F6 6 · abs EE 6 · abs,X FE 7 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| INX | X + 1 → X | impl E8 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| INY | Y + 1 → Y | impl C8 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| JMP | (PC+1) → PCL, (PC+2) → PCH | abs 4C 3 · (abs) 6C 5 (page wrap, §6) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| JSR | PC + 2 ↓, (PC+1) → PCL, (PC+2) → PCH | abs 20 6 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| LDA | M → A | # A9 2 · zp A5 3 · zp,X B5 4 · abs AD 4 · abs,X BD 4+p · abs,Y B9 4+p · (zp,X) A1 6 · (zp),Y B1 5+p | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| LDX | M → X | # A2 2 · zp A6 3 · **zp,Y** B6 4 · abs AE 4 · **abs,Y** BE 4+p | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| LDY | M → Y | # A0 2 · zp A4 3 · zp,X B4 4 · abs AC 4 · abs,X BC 4+p | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| LSR | 0 → [7…0] → C | A 4A 2 · zp 46 5 · zp,X 56 6 · abs 4E 6 · abs,X 5E 7 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| NOP | none | impl EA 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| ORA | A ∨ M → A | # 09 2 · zp 05 3 · zp,X 15 4 · abs 0D 4 · abs,X 1D 4+p · abs,Y 19 4+p · (zp,X) 01 6 · (zp),Y 11 5+p (B-20 prints "5" without the asterisk, as for AND; A governs) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| PHA | A ↓ | impl 48 3 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| PHP | P ↓ (B = 1 and bit 5 = 1 in the pushed byte, §6 *Decision*) | impl 08 3 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| PLA | A ↑ | impl 68 4 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| PLP | P ↑ | impl 28 4 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| ROL | C ← [7…0] ← C | A 2A 2 · zp 26 5 · zp,X 36 6 · abs 2E 6 · abs,X 3E 7 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| ROR | C → [7…0] → C | A 6A 2 · zp 66 5 · zp,X 76 6 · abs 6E 6 · abs,X 7E 7 (B-23 repeats "available … after June, 1976"; §1 revision decision) | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| RTI | P ↑, PC ↑ | impl 40 6 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| RTS | PC ↑, PC + 1 → PC | impl 60 6 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| SBC | A − M − C̄ → A (C̄ = borrow) | # E9 2 · zp E5 3 · zp,X F5 4 · abs ED 4 · abs,X FD 4+p · abs,Y F9 4+p · (zp,X) E1 6 · (zp),Y F1 5+p | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| SEC | 1 → C | impl 38 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| SED | 1 → D | impl F8 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| SEI | 1 → I | impl 78 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| STA | A → M | zp 85 3 · zp,X 95 4 · abs 8D 4 · abs,X 9D 5 · abs,Y 99 5 · (zp,X) 81 6 · (zp),Y 91 6 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| STX | X → M | zp 86 3 · **zp,Y** 96 4 · abs 8E 4 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| STY | Y → M | zp 84 3 · zp,X 94 4 · abs 8C 4 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| TAX | A → X | impl AA 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| TAY | A → Y | impl A8 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| TSX | S → X | impl BA 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| TXA | X → A | impl 8A 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| TXS | X → S | impl 9A 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |
| TYA | Y → A | impl 98 2 | tests/gen_cycles6502.py seeds 1-3 (every mode, every cycle) | done (PASS, logs/rtl-run1, rtl-run2) |

## §8 behaviours

| ID | Behaviour | Test | Status |
|---|---|---|---|
| C1 | Every documented opcode in every addressing mode: registers, memory and flags per §6 | random programs of all 151 opcodes in every mode with random registers, P (incl. D) and memory, every cycle compared on the pins, and a neutral state dump (PHP; PHA; STX; STY; PLA; PLP) after about every third instruction so a wrong A, X, Y, S or flag shows at the next dump; each opcode executed >= 17 times (`tests/gen_cycles6502.py`). A mutant in the ALU's decimal path is caught | done (PASS, logs/rtl-run2) |
| C2 | Pin timing per §4 for every addressing mode, incl. dummy cycles, page crossings and RMW double writes | `tests/gen_cycles6502.py` + `tb/tb_cyc6502.sv`: a, rw, sync, d_oe and the written data in every cycle of the three programs (random indexes: page crossings and zero-page wraps both occur) | done for instructions (PASS, logs/rtl-run1); interrupts and RESET sequences with C4/C6 |
| C3 | RDY: stops reads at any read cycle, ignored on writes | `tests/gen_cycles6502.py` seed 4: seed 3's program with RDY low in 1-4 clock runs landing anywhere (2,082 of 12,013 clocks): a read with RDY low repeats with the same address and SYNC, a write completes, the stop comes at the next read; every cycle compared, state dumps catch any effect on registers | done (PASS, logs/rtl-run3) |
| C4 | Interrupts: IRQ masked by I, NMI edge, BRK, B in the pushed P, and every case of the §6 poll rule: the poll point, the branch delay, old I after CLI/SEI/PLP vs new I after RTI, NMI visibility, NMI over IRQ, the first handler instruction, no hijack | `tests/gen_cycles6502.py` seeds 5-8: random programs with IRQ and NMI raised at random instruction starts (and more often before CLI/SEI/PLP/RTI/branches), expected cycles of every sequence (7 cycles, B = 0 in the pushed P, PC pushed as is, vectors FFFA/FFFE, I set) and of the poll decisions from the poll rule: **810 IRQ and 809 NMI sequences** across the four seeds, after CLI 4, SEI 4, PLP 321, RTI 765, taken-same-page branches 27, other branches 37 (counts in logs/rtl-run5/interrupt-causes.log); BRK (random BRK macro) is covered by C1 (its B = 1 push) and has no poll. A model without the taken-branch delay fails seed 5 | done (PASS on the RTL, logs/rtl-run5, repeated in rtl-run7 with the spec's reset timing) |
| C5 | Decimal mode per §6: A, C and NMOS N/V/Z, all 256 x 256 operands and both carries | block level: `tests/alu/run.sh` (ALU, 991,232 vectors, PR #16); CPU level: `tests/c5/gen_decimal.py` + `tb/tb_trace6502.sv`, a 6502 program that loops over every A x operand x carry with D = 1 for ADC and for SBC (131,072 cases each), writing A and the pushed P; expected from the spec-derived model: both PASS on the RTL (about 5m45s each). Clark's test (Homer's acceptance runner) is the independent cross-check | done (PASS, logs/rtl-run6, logs/alu-pr16) |
| C6 | Reset sequence and vectors | `tests/gen_cycles6502.py` seeds 1-8 and `cyc_r0..r7` (reset in the middle of the run at 8 consecutive cycles, held 10 clocks; RAM keeps its writes, the program restarts from the vector; while res_n = 0 and in reset cycles 1-7 rw = 1 and d_oe = 0; vector reads in cycles 6-7 at FFFC/FFFD; first SYNC in cycle 8; spec 5 and #30). All 16 runs PASS on main's RTL with the spec's timing (my first version of the testbench counted the reset cycles one early: #37, fixed) | done (PASS, logs/rtl-run7) |
| C7 | No X/Z, no bus conflict, with mutants and the positive bus_conflict case | `tb/tb_sys6502.sv` + `tests/c7/run.sh`: the decimal ADC and SBC programs on `m6502_system` (40,000 values each), every output of the system checked each clock for X/Z, bus_conflict = 0, d_oe = NOT rw; `tests/c7/mutant.sh`: d_oe stuck 1 makes bus_conflict rise (the positive case, `+EXPECT_CONFLICT`), d_out Z when idle fails the X/Z check, rw stuck 0 fails d_oe = NOT rw: all caught. The CPU pins are also checked for X/Z and d_oe = NOT rw in every `tb_cyc6502` run (16 runs) | done (PASS, logs/rtl-run8) |
| C8 | Random programs vs the reference model | Beru | n/a |

## Cross-check against SingleStepTests/65x02 (spec 9 item 2, a cross-check not ground truth)

`tests/sst_crosscheck.py` runs my machine model (`tests/mach6502.py`, written from spec 4.1/6.1) against all 151 documented opcode files, 10,000 tests each (cycle-by-cycle bus activity, final registers, P and RAM): **1,510,000 tests, 0 differences** with the taken-branch cycles as Igris decided in chip-6502#19/#21 (T2 = PC+2, page-cross T3 = the uncarried target; this is the model's only behaviour since #21 merged); the check also asserts that the model never reads an address the vector does not list. Decimal mode (ADC/SBC with D = 1, spec 6 Decision) agrees with the vectors on every operand they sample.

## MOS Programming Manual examples (spec 9 item 3)

`tests/pm/run_pm.py` (step `pm` of `tests/run_4state.sh`, bench `tb/tb_pm6502.sv`): our own transcription of the examples below from the page images of 6500-50A (Jan 1976), assembled with `tests/asm6502.py`, run on `m6502_system`; each program writes only what the manual prints to $7000 and the testbench compares it (plus X/Z and bus_conflict). **26 runs, 26 PASS**: `logs/pm-20261123/pm.log`. Page numbers are the **printed** page numbers (this scan: printed 9 = PDF 20, printed 70 = PDF 83; the offset changes along the book). Negative check done: a wrong printed value and a wrong clock count both make the run FAIL.

| Example | Page | What the manual prints, and we check | Result |
|---|---|---|---|
| 2.1 | 7 | 13 + 211 + carry-in 1 = 225, Carry 0 | PASS |
| 2.2 | 8 | 254 + 6 + carry-in 1 = 5, Carry 1 | PASS |
| 2.3 with 2.4's numbers | 9 | 258 + 4112 = 4370; carry 0 after the low add and after the high add | PASS |
| 2.3 with 2.5's numbers | 10 | 384 + 128 = 512; carry 1 after the low add, 0 after the high add | PASS |
| 2.6, 2.7, 2.8, 2.9, 2.10, 2.11 | 11-13 | A, Carry and Overflow for +5+7, +127+2, +5-3, +5-7, -5-7, -66-65 | PASS (6 runs) |
| 2.12 | 13 | decimal 79 + 14 = 93 | PASS |
| 2.13, 2.14 | 15, 16 | 5 - 3 = +2 Carry 1; 5 - 6 = -1 (FF) Carry 0 | PASS |
| 2.15 with 2.16's / 2.17's numbers | 17, 18 | 512 - 255 = 0x0101, carries 0 then 1; 255 - 512 = 0xFEFF (-257), carries 1 then 0 | PASS (2 runs) |
| 2.18 | 19 | decimal 44 - 29 = 15 | PASS |
| 2.19, 2.20 (X = 0 and 1) | 21 | AND clears bit 3: 1100 0111; ORA sets it: 1110 1111 | PASS (4 runs) |
| 2.21 | 22 | 1010 1111 EOR FF = 0101 0000 | PASS |
| 6.1 | 70 | five values moved; zero page, 30 cycles (p.74) | PASS, 30 clocks |
| 6.2 | 72 | self-modifying move loop moves five values | PASS |
| 6.4 | 76 | five values moved with X; 15 cycles per value, zero page (p.77 "from 15 cycles") | PASS, 5 x 15 - 1 = 74 clocks (the last BNE falls through) |
| 6.5 | 77 | five values moved counting X down; 13 cycles per value (p.77 "to 13 cycles") | PASS, 5 x 13 - 1 = 64 clocks |
| 6.16 (printed "Example: 6.16", p.94) | 94 | N < 256 move, absolute; N = 200 | PASS |

Where the manual prints no data (chapter 6) the data and the result dump are ours, and what is checked is that the printed operation moves the bytes and writes nothing else (sentinels).

**Not checkable (not in the pass count):**

| Example | Page | Why |
|---|---|---|
| 6.2 "125 cycles" (25 per pass) | 74 | our count for the listing is 27 per pass (CMP 2, BNE taken 3); the manual's sum does not follow from its own Appendix A table, which C2 checks. Not a RTL disagreement: the text is a loose estimate. |
| 6.4 "13 or 15 bytes / cycles" | 76 | ambiguous: two figures for one loop. We use the 15 that p.77 repeats. |
| 6.16 cycle column, "13 cycles" | 94 | lists STA abs,X as 4 cycles; Appendix A (A.3.4) says 5. Only the zero-page form (Example 6.5) gives 13, so no timing check on this one. |
| 6.17 (printed "Example 6.17", N > 256) | 95 | the listing's tail (BMI OUT / BNE LOOP / LDY #COUNT / BNE LOOP) cannot be assembled unambiguously from the print, and no result is printed. |
| 10.2 | 150 | the table shows ROL A taking 4 cycles with a fetch at 102; Appendix A says 2 cycles. Contradiction inside the manual, nothing to run. |
| 4.8, 4.x fragments | 36-48 | listings with symbolic addresses (ADL1, ADH1, "+50") and no printed result. |
| 9.1, 9.2, 9.6 | 127, 131, 141 | already the basis of spec 4/5/6 (cycle tables); covered by C1-C6, not repeated here. |
| Chapters 5, 8, 9 (others), 11 | | not individually triaged in this pass. The listed ones are the examples with printed results found in chapters 2, 6 and 10. **Open follow-up** if Sai wants every example accounted for. |

## CI

`tests/run_4state.sh` is the toolchain's hook (toolchain v0.9 `run_tests.sh` calls it): selftests, the model cross-check against `ref/`, the ALU block vectors, the 16 cycle-by-cycle runs (C1-C4, C6) and C7 with its mutants, the Programming Manual examples (`pm`), about 2 minutes, logs in the run dir; `FULL=1` adds the CPU-level decimal runs for a nightly job. A mutant in the ALU turns it red (logs/ci-run1).

## Tools

- `tests/mach6502.py`: cycle-accurate model (all 151 opcodes, per-cycle addresses/data, decimal mode, JMP-indirect wrap, B bit) from spec 4.1/6.1; `tests/mach6502_selftest.py` checks all 151 cycle counts against spec 6.1's table (PASS).
- `tests/asm6502.py`: assembler with the 151 opcodes of §6.0; `tests/asm6502_selftest.py` checks its table against the spec file and that every (mnemonic, mode) assembles to its byte (PASS).
