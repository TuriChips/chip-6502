# C8 full run on main 6b4ab4f (clean clone; harness 57dbd75 in a detached worktree)

20 chunks of `run.py --nprog 500 --nst 7000 --seed S`, S = 101..120.

| | total |
|---|---|
| programs | 10,001 |
| mismatching programs | **1** (seed 108, program 310: chip-6502#42, an NMI edge at the NMI sequence's T0 lost under a 2+ cycle RDY hold; fixed by #43, where this chunk passes) |
| cycles compared | 67,221,320 |
| instructions | 14,424,616 (1,442 per program) |
| IRQ / NMI sequences | 1,036,321 / 88,475 |
| RDY-held read cycles | 5,945,017 |
| stopped at an undocumented byte | 580 |

The chunk script kept only the last 4 lines of each chunk, which cut the MISMATCH line; the program was found by rerunning seed 108.
