#!/usr/bin/env bash
# Leo: sky130 flow for m6502: Yosys map -> OpenROAD place+route -> KLayout GDS + PNG.
# Usage: source <toolchain>/scripts/eda-env.sh; synth/sky130/run.sh   (outputs in synth/sky130/, logs in synth/sky130/logs/)
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
D=synth/sky130; mkdir -p $D/logs; W=$(mktemp -d)
S=$PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_hd
python3 -I $D/filter_lib.py $S/lib/sky130_fd_sc_hd__tt_025C_1v80.lib $W/f.lib | tee $D/logs/filter_lib.log
# TOP, SRC, PERIOD_NS can be overridden; m6502_mem and m6502_system are test fixtures and are not synthesized.
TOP=${TOP:-m6502}; PERIOD_NS=${PERIOD_NS:-1000}; export TOP PERIOD_NS
SRC=${SRC:-"rtl/top.v $(ls rtl/control/m6502_*.v rtl/datapath/m6502_*.v | grep -v -e m6502_mem -e m6502_system | tr '\n' ' ')"}
yosys -l $D/logs/yosys_full.log -q -p "read_liberty -lib $W/f.lib; read_verilog $SRC;
 hierarchy -check -top $TOP; synth -flatten -top $TOP;
 dfflegalize -cell \$_DFF_P_ 01 -cell \$_DLATCH_P_ x;
 dfflibmap -liberty $W/f.lib; abc -D $((PERIOD_NS*1000)) -liberty $W/f.lib; opt_clean -purge; check -assert;
 tee -o $D/logs/stat.txt stat -liberty $W/f.lib; write_verilog -noattr -noexpr $D/${TOP}_sky130.v"
TOP=$TOP OUT=$W NETLIST=$D/${TOP}_sky130.v LIB=$W/f.lib openroad -no_init -exit $D/flow.tcl 2>&1 | grep -v Nesterov | tee $D/logs/openroad.log
cp $W/${TOP}.def $D/${TOP}.def; cp $W/route_drc.rpt $D/logs/route_drc.rpt
klayout -b -r $D/render.py -rd def=$D/${TOP}.def -rd gds=$D/${TOP}.gds -rd png=$D/layout.png -rd top=$TOP -rd pdk=$PDK_ROOT/sky130A 2>&1 | tee $D/logs/klayout.log
echo "DRC (router) violations: $(grep -c violation $D/logs/route_drc.rpt || true)"
