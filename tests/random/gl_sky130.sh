#!/usr/bin/env bash
# C8 on the sky130 gate-level netlist (Beru, chip-6502#46): synth/sky130/m6502_sky130.v in place of the RTL m6502,
# PDK functional cell models, zero delay, Icarus (4-state, so X/Z after reset shows up as a mismatch; Verilator
# can't run the PDK's mux UDPs). Runs C8 (random RDY/IRQ/NMI per §6), C8 with mid-run resets, and the directed
# NMI cases. Each simulation is cut off after GL_TIMEOUT seconds (default 3600) and counts as FAIL.
# Needs PDK_ROOT (source <toolchain>/scripts/eda-env.sh); SKIP if it or the netlist is missing.
# Usage: tests/random/gl_sky130.sh [NPROG NST SEED]   default: 50 7000 1
set -u
cd "$(git rev-parse --show-toplevel)"
cells="${PDK_ROOT:-/nonexistent}/sky130A/libs.ref/sky130_fd_sc_hd/verilog"
net=synth/sky130/m6502_sky130.v
if [ ! -f "$cells/sky130_fd_sc_hd.v" ] || [ ! -f "$net" ]; then
  echo "SKIP gate-level sky130 (need $net and PDK_ROOT with sky130A cell models)"; exit 0
fi
dir=build/gl_sky130/src; rm -rf "$dir"; mkdir -p "$dir"
cp "$net" "$dir/"
n=${1:-50}; st=${2:-7000}; seed=${3:-1}
gl=(--timeout "${GL_TIMEOUT:-3600}" --rtl "$dir" --extra "$cells/primitives.v" "$cells/sky130_fd_sc_hd.v" --define FUNCTIONAL UNIT_DELAY=)
rc=0
python3 -I -B tests/random/c8/run.py "${gl[@]}" --out build/gl_sky130/c8 --nprog "$n" --nst "$st" --seed "$seed" || rc=1
python3 -I -B tests/random/c8/run_resets.py "${gl[@]}" --out build/gl_sky130/c8r --nprog "$((n / 5 + 1))" --nst 12000 --seed "$((seed + 1000))" || rc=1
[ $rc -eq 0 ] && echo "PASS gate-level sky130 C8" || echo "FAIL gate-level sky130 C8"
exit $rc
