#!/usr/bin/env bash
# Homer: the 6502 demo. From the repo root: ./sw/run_demo.sh   Output: logs/demo/demo.log (first line = the commit the run was made on)
# Builds the demo image (sw/demo/build_demo.py), runs it on the RTL under Verilator, and compares the console output with sw/demo/expected.txt.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"
mkdir -p logs/demo build/demo
stamp="commit: $(git rev-parse HEAD)$(git diff --quiet HEAD -- . ':(exclude)logs' || echo ' (+ uncommitted changes)')"
d=build/demo; python3 sw/demo/build_demo.py $d/demo.hex || exit 1
img="$(pwd)/$d/demo.hex"
verilator --cc --exe -Wno-fatal -Wno-lint -Wno-style -O3 --top-module tb_top -Mdir $d/obj -DMEMFILE="\"$img\"" -CFLAGS "-O2" \
  sw/demo/tb_top.sv $(find rtl -name '*.v' | sort) "$(pwd)/sw/demo/sim_main.cpp" > $d/verilator.log 2>&1 \
  && make -C $d/obj -f Vtb_top.mk -j"$(nproc)" >> $d/verilator.log 2>&1 \
  || { tail -n 20 $d/verilator.log >&2; echo "verilator build failed" >&2; exit 1; }
$d/obj/Vtb_top > $d/demo.console
{ echo "$stamp"; cat $d/demo.console; } > logs/demo/demo.log
got=$(grep -v -E '^(bus_conflict seen|TRAP|TIMEOUT)' $d/demo.console)
grep -q '^bus_conflict seen 0 times' $d/demo.console || { echo "DEMO FAIL: bus_conflict seen or no such line" | tee -a logs/demo/demo.log; exit 1; }
grep -q '^TRAP pc=0237' $d/demo.console || { echo "DEMO FAIL: the program did not spin at 0237h" | tee -a logs/demo/demo.log; exit 1; }
if [ "$got" = "$(cat sw/demo/expected.txt)" ]; then echo "DEMO PASS: printed '$got'" | tee -a logs/demo/demo.log
else echo "DEMO FAIL: printed '$got', expected '$(cat sw/demo/expected.txt)'" | tee -a logs/demo/demo.log; exit 1; fi
