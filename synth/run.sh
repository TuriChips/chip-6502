#!/usr/bin/env bash
# Leo: generic Yosys synthesis of m6502 alone (m6502_mem and m6502_system are test fixtures, not synthesized).
# Usage: synth/run.sh   -> synth/report.txt, synth/logs/yosys.log
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
mkdir -p synth/logs
TOP=${TOP:-m6502}
[ -n "${SRC:-}" ] || [ -f rtl/top.v ] || { echo "rtl/top.v not on main yet (set SRC and TOP to try other sources)"; exit 2; }
SRC=${SRC:-"rtl/top.v $(ls rtl/control/m6502_*.v rtl/datapath/m6502_*.v | grep -v -e m6502_mem -e m6502_system | tr '\n' ' ')"}
yosys -q -l synth/logs/yosys.log -p "
read_verilog $SRC;
hierarchy -check -top $TOP;
proc; flatten; opt; memory -nomap; memory_map; opt; techmap; opt;
abc -g AND,NAND,OR,NOR,XOR,XNOR,ANDNOT,ORNOT,MUX; opt_clean -purge;
check -assert;
tee -o synth/report.txt stat;
tee -a synth/report.txt ltp -noff
"
echo "--- warnings ---"; grep -i warning synth/logs/yosys.log | grep -v 'combinational (run' || echo none
grep -E 'Number of cells|\$_' synth/report.txt; grep 'length=' synth/report.txt
