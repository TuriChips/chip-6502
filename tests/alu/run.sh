#!/usr/bin/env bash
# Block-level check of m6502_alu (blocks.md section 3) against the spec-derived model: tests/alu/run.sh [rtl/datapath/m6502_alu.v]
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"; mkdir -p build logs
python3 tests/alu/gen_vectors.py build/alu_vectors.hex
iverilog -g2012 -o build/alu.vvp tests/alu/tb_alu.sv "${1:-rtl/datapath/m6502_alu.v}"
vvp -n build/alu.vvp +VEC=build/alu_vectors.hex +N=$(( $(wc -l < build/alu_vectors.hex) / 2 )) | tee logs/alu_run.log
grep -q '^PASS' logs/alu_run.log
