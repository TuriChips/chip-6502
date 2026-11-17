#!/usr/bin/env bash
# Homer: Dormann's 6502 functional test on the RTL under Verilator (spec section 9 item 1). From the repo root.
# Fetches the pinned test (sw/dormann/fetch.sh), loads it with the reset vector set to 0400h (bin2hex.py), runs until the program
# traps, and judges with check_trap.py (pass = the trap is the success trap at 3469h). Log: logs/dormann/functional.log (first line = commit).
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"
mkdir -p logs/dormann build/dormann
./sw/dormann/fetch.sh || exit 1
stamp="main commit: $(git rev-parse HEAD)$(git diff --quiet HEAD -- . ':(exclude)logs' || echo ' (+ uncommitted changes)')"
d=build/dormann; python3 sw/dormann/bin2hex.py $d/6502_functional_test.bin $d/functional.hex || exit 1
img="$(pwd)/$d/functional.hex"
verilator --cc --exe -Wno-fatal -Wno-lint -Wno-style -O3 --top-module tb_top -Mdir $d/obj -DMEMFILE="\"$img\"" -CFLAGS "-O2" \
  sw/dormann/tb_top.sv $(find rtl -name '*.v' | sort) "$(pwd)/sw/dormann/sim_main.cpp" > $d/verilator.log 2>&1 \
  && make -C $d/obj -f Vtb_top.mk -j"$(nproc)" >> $d/verilator.log 2>&1 \
  || { tail -n 20 $d/verilator.log >&2; echo "verilator build failed" >&2; exit 1; }
$d/obj/Vtb_top +MAXCLK="${MAXCLK:-2000000000}" > $d/functional.console
{ echo "$stamp"; cat $d/functional.console; } > logs/dormann/functional.log
python3 sw/dormann/check_trap.py functional logs/dormann/functional.log | tee -a logs/dormann/functional.log
exit "${PIPESTATUS[0]}"
