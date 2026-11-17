# synth/ (Leo)
Only `m6502` is synthesized. `m6502_mem` and `m6502_system` are test fixtures. All numbers below are from one run on **main 7e2124f** (includes #43, the NMI edge counter); regenerate with the scripts in this folder.

## Generic Yosys (`synth/run.sh` → `synth/report.txt`, `synth/report_hier.txt`, `synth/logs/yosys.log`)
Gate set AND/NAND/OR/NOR/XOR/XNOR/ANDNOT/ORNOT/MUX. The scripts use `memory -nomap -nordff`: without `-nordff`, Yosys merges the registered case-table inputs into inferred ROM read ports and rebuilds them, which added 23 flops that are not in the RTL (found in chip-6502#47).

| Item | Result |
|------|--------|
| Cells | 2,499: 119 flops and 2,380 gates |
| Flops per module (`report_hier.txt`, before flattening) | `m6502_regs` 66, `m6502_control` 32, `m6502_alu` 14, `m6502_timing` 7 = 119; `m6502`, `m6502_decode`, `m6502_plan` none |
| Longest path (flop to flop, `ltp -noff`) | 60 cells |
| Warnings, latches | none inferred, `check -assert` clean |

## sky130 layout (`synth/sky130/run.sh`, needs `source <toolchain>/scripts/eda-env.sh`)
Yosys maps `m6502` to `sky130_fd_sc_hd` at the typical corner (library `sky130_fd_sc_hd__tt_025C_1v80`; `lpflow_*`, probe and delay cells filtered out by `filter_lib.py`), OpenROAD places and routes (`flow.tcl`), KLayout writes `m6502.gds` and `layout.png`. Clock 1000 ns (1 MHz, my choice: the spec has no electrical timing). Tools: OpenROAD 2.0_3175, KLayout 0.30.13, sky130A PDK 1.0.471 (pinned in the toolchain `VERSIONS`).

| Item | Result | Log |
|------|--------|-----|
| Cells after mapping | 2,058, of which 119 are `dfxtp_1` flops | `sky130/logs/stat.txt` |
| Cell area | 13,880 µm² (14,449 µm² placed with 455 tap cells, 42% utilization) | `sky130/logs/stat.txt`, `sky130/logs/openroad.log` |
| Die | 196.3 × 196.3 µm | `sky130/logs/openroad.log` |
| Routed wire length, vias | 65,474 µm, 17,721 | `sky130/logs/openroad.log` |
| Worst register-to-register path | 9.239 ns data arrival + 0.117 ns setup, `_3964_` to `_3856_`, so about 9.4 ns, roughly 106 MHz; slack 990.6 ns at the 1000 ns clock | `sky130/logs/sta.log` |
| Worst path to an output pin (after routing) | 9.939 ns from flop `_3964_` through 30 gates to `d_out[6]`, outputs constrained at 0 ns delay; slack 990.1 ns | `sky130/logs/openroad.log` |
| Router DRC violations | 0 (the router's own count, not a signoff) | `sky130/logs/openroad.log` |

Timing basis: OpenSTA inside OpenROAD 2.0_3175, ideal clock, no wire parasitics. The register-to-register figure is on the mapped netlist before placement (`sta.tcl`); the output-pin figure is after routing but also without parasitics. Wire delay would add to both.

Not done: timing closure, power, clock tree, signoff DRC and LVS, gate-level simulation of `m6502_sky130.v` (chip-6502#46, Beru). Power is met1 rails plus met4 straps, 455 tap cells, no fill or decap: fine for a picture and a first run, not for fabrication. `synth/sky130/layout.png` is the image for the website card.

## Scripts
`TOP=` and `SRC=` override the top module and sources, `PERIOD_NS=` the clock period. With the 4004 and 74181 sources the same scripts reproduce the numbers in those repos.
