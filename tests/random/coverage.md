# 6502 C8 coverage (Beru, chip-6502#6)

What C8's random programs exercise, counted by `tests/random/c8/coverage.py`. It replays a C8 run's recorded inputs through the model; the RTL's agreement on all of it is C8's own log. Latest, on main 28bfbd6: `logs/c8-coverage-main-20261118T015517Z/coverage.txt` (1,000 programs × 7,000 cycles, seed 206, 0 mismatches; 151/151 opcodes, 61/61 behaviours).

## Exercised
- **Opcodes:** all 151 documented (§6.0). The 105 undocumented bytes aren't tested (§6), and a program reaching one stops being compared there.
- **Addressing (§4.1):**
  - indexed reads abs,X / abs,Y / (zp),Y, with and without a page cross;
  - indexed stores (the dummy read is always there);
  - RMW double writes in all 4 modes;
  - JMP (ind) with and without the $xxFF wrap.
- **Branches:** all 8, each not taken, taken on the same page, and taken across a page.
- **Decimal mode:** ADC and SBC, in both D = 1 and binary.
- **BRK, IRQ and NMI sequences.**
- **RDY:** holds on opcode fetches and on other reads, and RDY low during writes (ignored).
- **§6 poll rule:**
  - CLI/PLP 1→0 with `irq_n` low: not taken right after, and taken one instruction later;
  - SEI/PLP 0→1: one IRQ right after;
  - RTI pulling I = 0: IRQ right after;
  - an NMI deferred by a taken no-cross branch's early poll;
  - an NMI detected at the poll edge itself;
  - NMI over IRQ at the same poll;
  - an NMI pending through a sequence (the first handler instruction runs);
  - a poll cycle repeated by RDY.
- **Reset (§5)**, by `run_resets.py`: mid-run resets, with the write undo and RAM compared at each reset.
- **C7** `bus_conflict` positive case, by `conflict_check.py`.

## Not yet exercised
None: all 61 listed behaviours occur (the rarest, RTI pulling I = 1 while I = 0 with `irq_n` low, twice in 1,000 programs; it did not occur in 200).

## Out of C8's scope (other tests own them)
- **S.O.:** held at 1 in C8 (§2); covered by a directed test (Titus).
- **RDY during reset:** not specified (#40); C8 keeps `rdy` = 1 there.
- **Gate-level netlist:** after Leo's synthesis (#7).
