# Blocks: MOS 6502 (Chip #3)

Owner: Igris (Architect) · Spec: `docs/spec.md` · Status: **v1**, signed off with the spec (turichips#32, Sai 2026-11-17); moves to `TuriChips/chip-6502`. Ada's must-fix items 1–6 from her early read are applied.

All blocks are synchronous to the single rising-edge `clk`, one 6502 cycle per clock (spec §1). `res_n` is synchronous and active low (spec §5). Only the pins of `m6502` (spec §2) and of `m6502_system` are normative for tests. The internal ports below are the contract **between Zura (control) and Ada (datapath)**, and a port change needs a PR the other reviews.

**Lessons from the 8080's contract, applied up front** (chip-8080#16, #20, #28, #37):
- every mux select has a code table here, not "control decides";
- separate write enables for A and for flags;
- a load path for an address whose high byte arrives in the **same** cycle as the jump, as the 8080's `pair_op` 13;
- the data-bus source select can reach every register that is ever stored (A, X, Y, P, PCH, PCL);
- a TMP latch for read-modify-write.

## 1. Block list

| Block | File | Owner | State it holds |
|-------|------|-------|----------------|
| `m6502_timing` | rtl/control/m6502_timing.v | Zura | T-state counter (T0…T6), RDY hold, interrupt/reset sequence state |
| `m6502_control` | rtl/control/m6502_control.v | Zura | IR, the per-instruction cycle plan (§4.1), pending IRQ/NMI latches, the TMP latch |
| `m6502_alu` | rtl/datapath/m6502_alu.v | Ada | A, P (N V – B D I Z C storage, B as the push value only) |
| `m6502_regs` | rtl/datapath/m6502_regs.v | Ada | X, Y, S, PC (16), the address latches ADL/ADH (BAL/BAH reuse them), the pointer latch PL (8), `ab_carry`, `br_sign` |
| `m6502` | rtl/top.v | Zura | none (wiring and the bus muxes) |
| `m6502_mem` | rtl/datapath/m6502_mem.v | Ada | 64 KiB RAM for tests (`$readmemh`), combinational read, write on the clock edge |
| `m6502_system` | rtl/control/m6502_system.v | Zura | console port, IRQ/NMI/RDY/SO stimulus inputs, `bus_conflict` |

## 2. Shared codes (control ↔ datapath)

`addr_sel` (3 bits), the source of `a`:

| code | `a` | used for |
|------|-----|----------|
| 0 | PC | opcode and operand fetches, implied dummy reads |
| 1 | {ADH, ADL} | absolute, indexed, and indirect targets |
| 2 | {00, ADL} | zero page and zero-page pointers (page-zero wrap, spec §4.1) |
| 3 | {01, S} | stack |
| 4 | {ADH, ADL} with ADH **uncarried** | the dummy read before a page cross (spec §4.1 A.2.5, A.3.6) |
| 5 | vector: {FF, Fx} | FFFA–FFFF, by `vec_sel` below |

`vec_sel` (3 bits), the vector byte read at `addr_sel` 5: 0 FFFA (NMI low), 1 FFFB (NMI high), 2 FFFC (RES low), 3 FFFD (RES high), 4 FFFE (IRQ/BRK low), 5 FFFF (IRQ/BRK high); 6, 7 unused (control never drives them).

`ab_op` (4 bits), the address-latch arithmetic in regs (8-bit adds, carry kept in `ab_carry` for the next cycle):

| code | operation |
|------|-----------|
| 0 | none |
| 1 | ADL ← `d_in` |
| 2 | ADH ← `d_in` |
| 3 | ADL ← ADL + X (8-bit, carry → `ab_carry`) |
| 4 | ADL ← ADL + Y (8-bit, carry → `ab_carry`) |
| 5 | ADH ← ADH + `ab_carry` |
| 6 | ADL ← ADL + 1 (8-bit, no carry: the zero-page pointer and the `JMP ($xxFF)` wrap, spec §6) |
| 7 | PC ← {`d_in`, ADL} (JMP abs, JSR: the high byte arrives in the jump's last cycle; the 8080 lesson) |
| 8 | PC ← {ADH, ADL} |
| 9 | **Branch** (Zura, chip-6502#9, #31): runs in T2, after T1's `pc_op` 1 has stepped PC past the offset, so PC = opcode + 2. **PC ← {PCH, PCL + `d_in`}** (8-bit low add; PC is not incremented here). **`d_in` here is TMP**, the offset that control latched at the end of T1 (TMP ← the data bus), because in T2 the data bus carries the discarded opcode at PC + 2; the top selects it with `regs_din_tmp` = 1. `br_sign` ← `d_in`[7]. `ab_carry` ← **page crossed** = carry out XOR `d_in`[7] (a forward offset crosses on carry 1, a backward one on carry 0), measured against PC = opcode + 2 (so at xFE/xFF the base page is x + 1, spec §6). Control issues it with `pc_op` 0 |
| 10 | PCH ← PCH + 1 if `br_sign` = 0, PCH − 1 if `br_sign` = 1 (control issues it only when `ab_carry` = 1) |
| 11 | PL ← `d_in`, ADL ← ADL + 1 (8-bit, no carry: zero-page wrap). T3 of (zp,X), T2 of (zp),Y: the target's low byte is kept while ADL still points at the pointer's high byte |
| 12 | ADH ← `d_in`, ADL ← PL (end of (zp,X): the target is now {ADH, ADL}) |
| 13 | ADH ← `d_in`, ADL ← PL + Y (8-bit, carry → `ab_carry`). End of (zp),Y; then a read at `addr_sel` 4 and `ab_op` 5 if `ab_carry` = 1 |
| 14 | ADH ← `d_in` **and** ADL ← ADL + X (8-bit, carry → `ab_carry`). T2 of absolute,X (reads, stores and RMW), so T3's address {ADH, ADL} is already BAL + X (Zura, chip-6502#9) |
| 15 | ADH ← `d_in` **and** ADL ← ADL + Y (8-bit, carry → `ab_carry`). The same for absolute,Y |

`ab_carry` and `br_sign` are registers, so control sees them in the cycle after the `ab_op` that set them. Only `ab_op` 3, 4, 9, 13, 14 and 15 write `ab_carry`; only 9 writes `br_sign`. (From Ada's read on turichips#32, items 1 and 3.)

`pc_op` (2): 0 none, 1 PC + 1, 2 PCL ← `d_in`, 3 PCH ← `d_in` (RTS/RTI pulls).
`s_op` (2): 0 none, 1 S − 1, 2 S + 1, 3 S ← X (TXS).

`alu_a_sel` (2 bits), the ALU's first operand `a_in`, muxed in `m6502` (top): 0 A (`a_out`), 1 X, 2 Y, 3 unused. Only the compares use 1 and 2 (CPX, CPY); everything else uses 0.

`alu_b_sel` (3 bits), the ALU's second operand `b`, muxed in `m6502`:

| code | `b` | used for |
|------|-----|----------|
| 0 | `d_in` | every memory operand, immediate, PLA/PLP |
| 1 | TMP | the RMW modify (ASL/LSR/ROL/ROR/INC/DEC on memory) |
| 2 | X | TXA, INX/DEX (op INC/DEC) |
| 3 | Y | TYA, INY/DEY |
| 4 | S | TSX |
| 5 | A | TAX, TAY, and the accumulator shifts (ASL A etc.) |
| 6, 7 | unused | |

**X and Y are written only from the ALU's `result`** (`wdata` = `result`, no mux). Every instruction that writes X or Y also sets N and Z (LDX, LDY, TAX, TAY, TSX, INX, INY, DEX, DEY), so it goes through op LD/INC/DEC with `f_we` = 1 and `a_we` = 0. S is written only by `s_op` (TXS is `s_op` 3, no flags). PC pulls come from `d_in` by `pc_op` 2/3. (Ada's items 2 and 4.)

`d_out_sel` (3 bits), the source of `d_out` on write cycles:

| code | value |
|------|-------|
| 0 | A |
| 1 | X |
| 2 | Y |
| 3 | P as pushed (B per `push_b`, bit 5 = 1; spec §3) |
| 4 | PCH |
| 5 | PCL |
| 6 | TMP (the RMW **unmodified** write) |
| 7 | ALU `result` (the RMW **modified** write, and INC/DEC) |

## 3. Ports

Datapath blocks take `reset`, **active high**, from the top (`reset` = NOT `res_n`, held for the whole time `res_n` = 0). It is synchronous. Spec §3 leaves A, X, Y, S and the unnamed P bits unreset, which tests must not read; Ada's blocks clear them to 0 anyway so a 4-state run never sees an X. After `reset` the datapath is: A, X, Y, S, ADL, ADH, PL, `ab_carry`, `br_sign` = 0, PC = 0 (control loads it from the vector), P with I = 1 and every other stored bit 0. (Ada, chip-6502#2.)

### `m6502_alu` (Ada)
| Port | Dir | Width | Meaning |
|------|-----|-------|---------|
| `clk`, `reset` | in | 1, 1 | |
| `op` | in | 5 | Table below |
| `a_in` | in | 8 | First operand, muxed in the top by `alu_a_sel` (A, X or Y) |
| `b` | in | 8 | Second operand, muxed in the top by `alu_b_sel` |
| `a_we` | in | 1 | A takes `result`. Ignored by CMP, BIT and the flag ops (they never write A) |
| `f_we` | in | 1 | The flags in the table below update. With `f_we` = 0 nothing in P changes |
| `pull_p` | in | 1 | PLP/RTI: P ← `b` (N V D I Z C from bits 7, 6, 3, 2, 1, 0; bits 5 and 4 ignored). Wins over `f_we` |
| `push_b` | in | 1 | The B bit of `p_push` (spec §6: 1 for BRK and PHP, 0 for IRQ and NMI) |
| `a_out` | out | 8 | A |
| `p_push` | out | 8 | P as pushed: `{N, V, 1, push_b, D, I, Z, C}` (`d_out_sel` 3) |
| `flags` | out | 4 | `{N, V, Z, C}`, for the branch conditions |
| `result` | out | 8 | Combinational result of `op` (feeds A, X, Y through `wdata`, and the RMW modified write) |

`op` (5 bits). "NZ" = N and Z from `result`. Decimal ADC/SBC follow spec §6 exactly when D = 1.
| `op` | Operation | Flags updated when `f_we` = 1 |
|------|-----------|--------------------------------|
| 0 | none (`result` = `a_in`) | none |
| 1 | ADC: `a_in + b + C` (decimal if D = 1) | N V Z C |
| 2 | SBC: `a_in + ~b + C` (decimal A if D = 1; N V Z C stay the binary SBC's) | N V Z C |
| 3, 4, 5 | AND, ORA, EOR: `a_in` op `b` | N Z |
| 6 | CMP: flags of `a_in − b`, `result` = `a_in − b` (CMP, CPX, CPY) | N Z C (C = `a_in` ≥ `b`) |
| 7 | BIT: `result` = `a_in & b` | N = `b`[7], V = `b`[6], Z = (`a_in & b`) = 0 |
| 8, 9 | ASL, LSR: shift `b` | N Z C |
| 10, 11 | ROL, ROR: rotate `b` through C | N Z C |
| 12, 13 | INC, DEC: `b ± 1` | N Z |
| 14 | LD: `result` = `b` | N Z |
| 15, 16 | CLC, SEC | C |
| 17, 18 | CLI, SEI | I |
| 19, 20 | CLD, SED | D |
| 21 | CLV | V |
| 22 | SEV: V ← 1 (the S.O. pin; added for control, chip-6502#26) | V |
| 23–31 | unused | none |
`a_we` = 1 is used with ADC, SBC, AND, ORA, EOR, ASL/LSR/ROL/ROR (accumulator forms, `b` = A), LD (LDA, TXA, TYA, PLA). X and Y writes (LDX, LDY, TAX, TAY, TSX, INX, INY, DEX, DEY) use `a_we` = 0, `f_we` = 1 and `x_we`/`y_we` in regs, as §2 says. The interrupt sequences set I with op 18 and `f_we` = 1.

### `m6502_regs` (Ada)
| Port | Dir | Width | Meaning |
|------|-----|-------|---------|
| `clk`, `reset` | in | 1, 1 | |
| `d_in` | in | 8 | For the `ab_op` and `pc_op` loads and the branch add. The top drives it with `regs_din_tmp` ? TMP : the data bus (TMP only for `ab_op` 9, see §2) |
| `wdata` | in | 8 | ALU `result`, the only source of X and Y (§2) |
| `x_we`, `y_we` | in | 1, 1 | X ← `wdata`, Y ← `wdata` |
| `ab_op` | in | 4 | §2 |
| `pc_op` | in | 2 | §2 |
| `s_op` | in | 2 | §2 |
| `addr_sel`, `vec_sel` | in | 3, 3 | §2 |
| `addr` | out | 16 | The address pins |
| `ab_carry` | out | 1 | Registered, §2 (carry of `ab_op` 3, 4, 13, or page crossed for 9) |
| `x_out`, `y_out`, `s_out` | out | 8 each | X, Y, S (`alu_b_sel` 2, 3, 4 and `d_out_sel` 1, 2 in the top) |
| `pc` | out | 16 | PC (`d_out_sel` 4, 5 use `pc[15:8]`, `pc[7:0]`; also the debug port) |

Rules (Ada, chip-6502#2):
- **`ab_op` and `pc_op` are independent fields and may act in the same cycle** (T1 of a zero-page access: `ab_op` 1 and `pc_op` 1). If both would write PC (`ab_op` 7, 8, 9 or 10 with `pc_op` ≠ 0), `ab_op` wins; control doesn't do this on purpose. `s_op` is independent of both.
- `ab_op` 5, 10 and 12 and the PCL halves of `pc_op` read the **registered** values of ADH, `ab_carry` and `br_sign`, so each takes effect a cycle after the one that set it, as §2 states.
- X and Y write only from `wdata` on `x_we`/`y_we`; `x_we` and `y_we` are never 1 together.
- `addr` is combinational from `addr_sel` and the registers.

### `m6502_mem` (Ada)
Parameter `INIT_FILE` (`$readmemh`, one byte per line, up to 65,536; empty = no file). Memory is zeroed first, so unlisted bytes read 00.
| Port | Dir | Width | Meaning |
|------|-----|-------|---------|
| `clk` | in | 1 | |
| `addr` | in | 16 | |
| `we` | in | 1 | Write `wdata` at `addr` on the rising edge. Driven by `m6502_system` in a write cycle (RDY doesn't stop writes, spec §2) |
| `wdata` | in | 8 | |
| `rdata` | out | 8 | Combinational: the byte at `addr`, always (a 6502 read cycle has no strobe) |

### `m6502_control` (Zura)
Everything in §2 as outputs, plus `regs_din_tmp` (1 bit: the top gives `m6502_regs` TMP instead of the data bus as `d_in`, for `ab_op` 9 only), `tmp` (8 bits, the TMP latch; T1 of a branch latches the offset into it, as the RMW read does), `rw`, `sync`, `d_oe` (= NOT `rw`, spec §4.0), the RDY hold, the TMP latch, `alu_a_sel`, `alu_b_sel`, `push_b`, `d_out_sel`, and the interrupt latches per spec §6. Its port table is Zura's to write, the way the 8080's was.

## 4. Who does what first (when the spec is signed off)
1. **Ada:** `m6502_alu` and `m6502_regs` against §2–§3 here, then `m6502_mem`.
2. **Zura:** `m6502_timing`, then `m6502_control` and `m6502`, then `m6502_system`.
3. **Titus:** C1–C7 on the pins, with `tests/coverage.md` per spec §8.
4. **Beru:** the pin-level reference model and C8, with SingleStepTests as a cross-check (spec §9).
5. **Leo:** synthesis and sky130 layout.
6. **Homer:** Dormann's test runner (fetched, pinned), the demo, the write-up.
7. **Tesla:** the `chip-6502` repo and toolchain wiring.
