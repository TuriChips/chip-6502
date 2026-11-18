#!/usr/bin/env bash
# Homer: Bruce Clark's decimal mode test on the RTL under Verilator (spec section 9 item 1, the C5 acceptance test for the decimal decision).
# Fetches the pinned source (fetch.sh), builds it with build_decimal.py (options as in the spec), runs it with the reset vector set to TEST,
# and judges with check_trap.py decimal. Log: logs/dormann/decimal.log (first line = the commit the run was made on).
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"
mkdir -p logs/dormann build/dormann
./sw/dormann/fetch.sh || exit 1
stamp="commit: $(git rev-parse HEAD)$(git diff --quiet HEAD -- . ':(exclude)logs' || echo ' (+ uncommitted changes)')"
d=build/dormann
python3 sw/dormann/build_decimal.py $d/6502_decimal_test.a65 $d/decimal.hex $d/decimal.labels || exit 1
printf '@FFFC 00 02\n' >> $d/decimal.hex                      # reset vector -> TEST (0200h)
spin=$(awk '$1=="SPIN"{print $2}' $d/decimal.labels)
img="$(pwd)/$d/decimal.hex"
verilator --cc --exe -Wno-fatal -Wno-lint -Wno-style -O3 --top-module tb_top -Mdir $d/dobj -DMEMFILE="\"$img\"" -CFLAGS "-O2" \
  sw/demo/tb_top.sv $(find rtl -name '*.v' | sort) "$(pwd)/sw/demo/sim_main.cpp" > $d/dverilator.log 2>&1 \
  && make -C $d/dobj -f Vtb_top.mk -j"$(nproc)" >> $d/dverilator.log 2>&1 \
  || { tail -n 20 $d/dverilator.log >&2; echo "verilator build failed" >&2; exit 1; }
$d/dobj/Vtb_top +MAXCLK="${MAXCLK:-2000000000}" > $d/decimal.console
{ echo "$stamp"; cat $d/decimal.console; } > logs/dormann/decimal.log
python3 sw/dormann/check_trap.py decimal logs/dormann/decimal.log "$spin" | tee -a logs/dormann/decimal.log
exit "${PIPESTATUS[0]}"
