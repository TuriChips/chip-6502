# synth/ (Leo)
Scripts only so far: `rtl/top.v` (`m6502`) is not on main yet (chip-6502#7 waits for it). Only `m6502` is synthesized; `m6502_mem` and `m6502_system` are test fixtures.

- `synth/run.sh`: generic Yosys (gate counts, flops, longest path), after `memory_map`. Writes `synth/report.txt`.
- `synth/sky130/run.sh`: Yosys map to `sky130_fd_sc_hd` (typical corner), OpenROAD place and route, KLayout GDS and `layout.png`. Needs `source <toolchain>/scripts/eda-env.sh`. Default clock period 1000 ns (a 1 MHz clock, the original's slowest grade; the spec has no electrical timing). `PERIOD_NS=...` overrides. Expect the routed run to take tens of minutes.
- `TOP=` and `SRC=` override the top module and sources. Skeleton check: with the 4004 and 74181 sources the same scripts reproduce the numbers in those repos (4004 generic: 1278 cells, path 25; 74181 sky130: 302 µm² placed, 1.014 ns, 0 router DRC violations).

Results come with the RTL.
