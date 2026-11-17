# C8 full run, chip-6502 (spec §8: >= 10,000 programs x 1,000 instructions)

RTL: local integration, see the first line of run.log and rtl_heads.txt. Model: ref/ref6502.py + ref/pins6502.py.
Command: 20 chunks of `tests/random/c8/run.py --nprog 500 --nst 7000 --seed S` (S = 1..20), defaults
`--rdy 10 --irq 30 --nmi 10`.

| | total |
|---|---|
| programs | 10,000 |
| mismatching programs | **0** |
| cycles compared (every pin, every cycle from reset cycle 8) | 55,578,297 |
| instructions | 11,791,221 (1,179 per program on average) |
| IRQ sequences | 677,925 |
| NMI sequences | 71,998 |
| RDY-held read cycles | 4,933,122 |
| programs stopped at an undocumented byte (§6, not tested) | 2416 |
| programs with reset cycles 3-5 not at S, S-1, S-2 | 0 |
