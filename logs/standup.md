# Standup log: chip-6502

## Beru, 2026-11-17/18
- **Passed:**
  - Model vs SingleStepTests: 1,510,000 vectors, 0 differences (`logs/sst-ref-20261117T120503Z/run.log`).
  - C8 on main 28bfbd6: 10,000 programs, 0 mismatches (`logs/c8-full-main-20261118T004520Z/SUMMARY.md`).
  - C8 with mid-run resets: 200 programs, 0 mismatches (`logs/c8-resets-main-20261118T015254Z/run.log`).
  - Coverage: 61/61 behaviours (`logs/c8-coverage-main-20261118T015517Z/coverage.txt`).
  - Gate level on the #55 netlist: C8 500 programs + 101 with resets + directed 8/8, DEF check PASS (`logs/c8-gl-sky130-pr55-20261117T221226Z/run.log`).
  - CI: `tests/random/run.sh` gives `PASS random` (#53).
  - Bugs found: #31, #32, #42 (RTL); #17, #25, #40 (spec).
- **In progress:** nothing assigned. #6 and #46 are closed.
- **Blocked:** nothing.
