#!/usr/bin/env bash
# Random-program cycle tests on the m6502 pins: generates (tests/gen_cycles6502.py) and runs the 4 seeds (4 = RDY stimulus). Exit 1 if any fails.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"
python3 tests/gen_cycles6502.py build/gen/c6502 >/dev/null; mkdir -p build logs; bad=0
for s in 1 2 3 4 5 6 7 8 r0 r1 r2 r3 r4 r5 r6 r7; do
  case $s in r*) n=$s;; *) n=s$s;; esac; b=build/gen/c6502/cyc_$n
  iverilog -g2012 -DMEMFILE="\"$b.hex\"" -o build/cyc_$s.vvp tb/tb_cyc6502.sv $(find "${RTL_DIR:-rtl}" -name '*.v') || { bad=$((bad+1)); continue; }
  r=$(plus=""; [ -f $b.plus ] && plus=$(cat $b.plus); vvp -n build/cyc_$s.vvp +EXP=$b.cyc +N=$(wc -l < $b.cyc) $plus | grep -E '^(PASS|FAIL)' | head -3); echo "seed $s: $r"; case "$r" in PASS*) ;; *) bad=$((bad+1));; esac
done
echo "cyc: $bad failing"; [ $bad -eq 0 ]
