#!/usr/bin/env bash
# Random-program cycle tests on the m6502 pins: generates (tests/gen_cycles6502.py) and runs the 3 seeds. Exit 1 if any fails.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"
python3 tests/gen_cycles6502.py build/gen/c6502 >/dev/null; mkdir -p build logs; bad=0
for s in 1 2 3; do
  b=build/gen/c6502/cyc_s$s
  iverilog -g2012 -DMEMFILE="\"$b.hex\"" -o build/cyc_s$s.vvp tb/tb_cyc6502.sv $(find "${RTL_DIR:-rtl}" -name '*.v') || { bad=$((bad+1)); continue; }
  r=$(vvp -n build/cyc_s$s.vvp +EXP=$b.cyc +N=$(wc -l < $b.cyc) | grep -E '^(PASS|FAIL)' | head -3); echo "seed $s: $r"; case "$r" in PASS*) ;; *) bad=$((bad+1));; esac
done
echo "cyc: $bad failing"; [ $bad -eq 0 ]
