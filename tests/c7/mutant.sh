#!/usr/bin/env bash
# C7 must be able to fail and bus_conflict must be seen to rise (the positive case). Mutants on a scratch copy of rtl/ (build/c7/mut_*, never the tree):
#   doe_on : d_oe stuck at 1 (the CPU drives the data bus in read cycles too) -> bus_conflict must rise (+EXPECT_CONFLICT=1)
#   rw_low : rw stuck at 0 with d_oe as is -> the CPU claims writes in read cycles, the program breaks: caught by the write trace or X/Z (normal run must FAIL)
#   dout_z : d_out is Z when not writing -> the normal run must FAIL with 'FAIL C7 X/Z'
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"
python3 tests/c5/gen_decimal.py build/gen/c5 >/dev/null; mkdir -p build/c7; ok=0; P=build/gen/c5/dec_adc
try() { # name file sed-expr mode(conflict|fail) pattern
  local d=build/c7/mut_$1; rm -rf "$d"; mkdir -p "$d"; cp -r rtl "$d/"; sed -i "$3" "$d/rtl/$2"
  cmp -s "rtl/$2" "$d/rtl/$2" && { echo "mutant $1: sed changed nothing"; ok=1; return; }
  iverilog -g2012 -DMEMFILE="\"$P.hex\"" -o $d/sim.vvp tb/tb_sys6502.sv $(find $d/rtl -name '*.v') || { echo "mutant $1: does not compile"; ok=1; return; }
  if [ "$4" = conflict ]; then out=$(vvp -n $d/sim.vvp +EXPECT_CONFLICT=1 +CLOCKS=20000); else out=$(vvp -n $d/sim.vvp +EXP=$P.exp +N=2000 +CLOCKS=60000); fi
  if grep -q "$5" <<<"$out"; then echo "mutant $1: caught ($(grep -m1 "$5" <<<"$out" | cut -c1-70))"; else echo "mutant $1: NOT caught"; ok=1; fi
}
try doe_on control/m6502_control.v 's/assign d_oe   = wr_cyc;/assign d_oe   = 1'"'"'b1;/' conflict '^PASS: bus_conflict rose'
try dout_z top.v 's/assign d_out = (d_out_sel == 3'"'"'d0)/assign d_out = ~d_oe ? 8'"'"'hzz : (d_out_sel == 3'"'"'d0)/' fail 'FAIL C7 X/Z'
try rw_low control/m6502_control.v 's/assign rw     = ~wr_cyc;/assign rw     = 1'"'"'b0;/' fail '^FAIL'
exit $ok
