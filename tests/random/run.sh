#!/usr/bin/env bash
# Beru's random tests for the 6502, run by the toolchain's `make test` / CI (chip-6502#52). Sized for a PR run
# (a few minutes); the full-size runs (C8 10,000 programs, gate level) are separate and logged under logs/.
#   1. ref/ref6502.py and ref/pins6502.py selftests (spec §4.1/§6.1 cycle counts, decimal examples, §6 poll rule)
#   2. C8: RTL vs model, every pin every cycle, random programs with random RDY/IRQ/NMI (spec §6)
#   3. C8 with mid-run resets (spec §5): reset rules, write undo, RAM compared at each reset
#   4. Directed C8: the NMI corners of chip-6502#42/#43
#   5. C7 positive bus_conflict check (a mutant CPU must raise it, the real one never)
#   6. SingleStepTests cross-check of the model: only if the vectors are already in build/sst (800 MB, fetched by
#      tests/random/sst/run.py); otherwise SKIP.
# Usage: tests/random/run.sh   Logs: $RUN_DIR/random-*.log (default logs/<timestamp>/)
set -u
cd "$(git rev-parse --show-toplevel)"
run="${RUN_DIR:-logs/$(date -u +%Y%m%dT%H%M%SZ)}"; mkdir -p "$run"
ok=0
step() { # name log cmd...
  local name=$1 log=$2; shift 2
  if "$@" >"$log" 2>&1 && grep -q '^PASS' "$log" && ! grep -q -E '^(FAIL|MISMATCH)' "$log"; then
    echo "PASS $name"
  else
    echo "FAIL $name ($log)"; ok=1
  fi
}
py() { python3 -I -B "$@"; }
step ref-selftest   "$run/random-ref-selftest.log"  py ref/ref6502.py
step pins-selftest  "$run/random-pins-selftest.log" py ref/pins6502.py
step c8             "$run/random-c8.log"            py tests/random/c8/run.py --nprog 100 --nst 5000 --seed 1 --out build/ci/c8
step c8-resets      "$run/random-c8-resets.log"     py tests/random/c8/run_resets.py --nprog 20 --nst 12000 --seed 1 --out build/ci/c8r
step c8-directed    "$run/random-c8-directed.log"   py tests/random/c8/directed.py --out build/ci/directed
step c7-conflict    "$run/random-c7-conflict.log"   py tests/random/c8/conflict_check.py
if [ "$(ls build/sst/*.json 2>/dev/null | wc -l)" -ge 151 ]; then
  step sst "$run/random-sst.log" py tests/random/sst/run.py --n 2000
else
  echo "SKIP sst (SingleStepTests vectors not in build/sst; tests/random/sst/run.py fetches them)"
fi
exit $ok
