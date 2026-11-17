# C8 full run, chip-6502 (spec §8: >= 10,000 programs x 1,000 instructions)

RTL: local integration of the open RTL PRs (first line of run.log, rtl_heads.txt). Model and harness: the commit
named in run.log's first line. Command: 20 chunks of `tests/random/c8/run.py --nprog 500 --nst 7000 --seed S`
(S = 1..20), defaults `--rdy 10 --irq 30 --nmi 10`; rdy = 1 until reset cycle 8 (#40).

| | total |
|---|---|
| programs | 10,000 |
| mismatching programs | **0** |
| cycles compared (every pin, every cycle from reset cycle 8) | 67,226,934 |
| instructions | 14,471,900 (1,447 per program on average) |
| IRQ sequences | 1,023,301 |
| NMI sequences | 88,250 |
| RDY-held read cycles | 5,957,293 |
| programs stopped at an undocumented byte (§6, not tested) | 569 (5.7%) |

Note: pins6502.py gained a behaviour-neutral trace hook (self.trace = None by default) at 2026-11-17 15:55:01 UTC, during: == chunk seed=8. Selftest PASS before and after.
