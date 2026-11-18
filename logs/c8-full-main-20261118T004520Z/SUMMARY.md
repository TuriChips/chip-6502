# C8 full run on main (closes the C8 target of chip-6502#6)

RTL and harness: main 28bfbd6 (detached worktree, untouched during the run). 20 chunks of `tests/random/c8/run.py --nprog 500 --nst 7000 --seed S`, S = 201..220 (new seeds),
defaults `--rdy 10 --irq 30 --nmi 10`. Every MISMATCH line is kept in run.log (none).

| | total |
|---|---|
| chunks / programs | 20 / 10,000 |
| mismatching programs | **0** (MISMATCH lines: 0) |
| cycles compared, every pin every cycle from reset cycle 8 | 67,226,062 |
| instructions | 14,461,584 (1,446 per program) |
| IRQ / NMI sequences | 1,014,634 / 88,489 |
| RDY-held read cycles | 5,957,661 |
| stopped at an undocumented byte (§6, not tested) | 575 (5.8%) |
