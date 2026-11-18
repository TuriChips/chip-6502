#!/usr/bin/env bash
# C7 (spec 8): no X/Z on any output of m6502_system and no bus_conflict while a real program runs (the decimal ADC/SBC programs of tests/c5, first 40,000 values each).
# Exit 1 on any failure.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"
python3 tests/c5/gen_decimal.py build/gen/c5 >/dev/null; mkdir -p build/c7; bad=0
for op in adc sbc; do
  b=build/gen/c5/dec_$op
  iverilog -g2012 -DMEMFILE="\"$b.hex\"" -o build/c7/$op.vvp tb/tb_sys6502.sv $(find "${RTL_DIR:-rtl}" -name '*.v') || { bad=$((bad+1)); continue; }
  r=$(vvp -n build/c7/$op.vvp +EXP=$b.exp +N=40000 | grep -E '^(PASS|FAIL)' | head -2 | tr '\n' ' '); echo "$op: $r"; case "$r" in PASS*) ;; *) bad=$((bad+1));; esac
done
echo "c7: $bad failing"; [ $bad -eq 0 ]
