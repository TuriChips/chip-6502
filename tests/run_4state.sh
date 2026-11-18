#!/usr/bin/env bash
# The toolchain's test hook (run_tests.sh calls tests/run_4state.sh): runs the 6502's C1-C7 suites (Icarus, 4-state) and exits 1 on any failure.
# Logs: $RUN_DIR/4state-<step>.log when RUN_DIR is set (the toolchain), else build/4state/logs/<step>.log (untracked).
# PR-sized by default (a few minutes). FULL=1 adds the long runs the 8080 left to its nightly job: the CPU-level decimal ADC and SBC over every A x operand x carry
# (131,072 cases each, about 6 minutes each). RTL_DIR (default rtl) lets the mutant check run the same steps on a modified copy.
#   selftests         asm6502 (opcode map vs spec), mach6502 (cycle counts vs spec 6.1)
#   crosscheck-ref    my model vs Beru's ref/ref6502.py, 20,000 random instructions (C1)
#   alu               m6502_alu block, 991,232 spec-model vectors (C5 at block level)
#   cycles            16 cycle-by-cycle runs on the pins: instructions, RDY, interrupts, resets (C1-C4, C6)
#   c7                system-level X/Z, bus_conflict, d_oe = NOT rw (C7), then its three mutants (the positive case)
#   decimal-cpu       (FULL=1) C5 at CPU level
set -u
cd "$(git rev-parse --show-toplevel)"
logdir="${RUN_DIR:-build/4state/logs}"; prefix=""; [ -n "${RUN_DIR:-}" ] && prefix="4state-"
mkdir -p "$logdir" build; rc=0
step() { # name cmd...
  local name=$1; shift; local log="$logdir/$prefix$name.log"
  if "$@" >"$log" 2>&1 && ! grep -qE '^FAIL|^mutant .*NOT caught' "$log"; then echo "PASS $name"; else echo "FAIL $name, see $log"; rc=1; fi
}
step selftests bash -c 'python3 tests/asm6502_selftest.py && python3 tests/mach6502_selftest.py'
[ -f ref/ref6502.py ] && step crosscheck-ref python3 tests/crosscheck_ref.py ref 20000 1
step alu tests/alu/run.sh
step cycles tests/run_cyc6502.sh
step c7 bash -c 'tests/c7/run.sh && tests/c7/mutant.sh'
if [ "${FULL:-}" = 1 ]; then
  step decimal-cpu bash -c 'python3 tests/c5/gen_decimal.py build/gen/c5 >/dev/null && for op in adc sbc; do
    iverilog -g2012 -DMEMFILE="\"build/gen/c5/dec_$op.hex\"" -o build/dec_$op.vvp tb/tb_trace6502.sv $(find "${RTL_DIR:-rtl}" -name "*.v") && vvp -n build/dec_$op.vvp +EXP=build/gen/c5/dec_$op.exp +N=262144 | tee /dev/stderr | grep -q "^PASS" || exit 1; done'
fi
exit $rc
