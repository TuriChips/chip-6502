# synth/ (Leo)
Only `m6502` is synthesized. `m6502_mem` and `m6502_system` are test fixtures.

## Generic Yosys (`synth/run.sh` → `synth/report.txt`, `synth/logs/yosys.log`)
Gate set AND/NAND/OR/NOR/XOR/XNOR/ANDNOT/ORNOT/MUX.

| Item | Result |
|------|--------|
| Cells | 2555: 140 flops and 2415 gates |
| Longest path (flop to flop, `ltp -noff`) | 53 cells |
| Warnings, latches | none inferred, `check -assert` clean |

## sky130 layout (`synth/sky130/run.sh`, needs `source <toolchain>/scripts/eda-env.sh`)
Yosys maps `m6502` to `sky130_fd_sc_hd` at the typical corner (`lpflow_*`, probe and delay cells filtered out by `filter_lib.py`), OpenROAD places and routes (`flow.tcl`), KLayout writes `m6502.gds` and `layout.png`. Clock 1000 ns (1 MHz, my choice: the spec has no electrical timing). Tools: OpenROAD 2.0_3175, KLayout 0.30.13, sky130A PDK 1.0.471 (pinned in the toolchain `VERSIONS`).

| Item | Result | Log |
|------|--------|-----|
| Cells after mapping | 2,089, of which 140 are `dfxtp_1` flops (generic gate set above: 2,555) | `sky130/logs/stat.txt` |
| Cell area | 14,440 µm² (15,017 µm² placed with 461 tap cells, 42% utilization) | `sky130/logs/stat.txt`, `sky130/logs/openroad.log` |
| Die | 200.0 × 200.0 µm | `sky130/logs/openroad.log` |
| Routed wire length, vias | 66,238 µm, 17,979 | `sky130/logs/openroad.log` |
| Longest path reported (typical corner, ideal clock, outputs constrained at 0 ns delay) | 9.545 ns from flop `_3950_` through 27 gates to output pin `d_out[7]`; slack 990.455 ns at the 1000 ns clock (met) | `sky130/logs/openroad.log` |
| Router DRC violations | 0 (the router's own count, not a signoff) | `sky130/logs/openroad.log` |

The worst reported path ends at an output pin, so it is a flop-to-pin delay and not a flop-to-flop Fmax. Any clock period above about 10 ns meets timing on this report, so it is far above the original's 1 to 2 MHz, but I have not computed a flop-to-flop Fmax.

Not done: timing closure, power, clock tree (ideal clock), signoff DRC and LVS, gate-level simulation of `m6502_sky130.v`. Power is met1 rails plus met4 straps, 461 tap cells, no fill or decap: fine for a picture and a first run, not for fabrication. `synth/sky130/layout.png` is the image for the website card.

## Scripts
`TOP=` and `SRC=` override the top module and sources, `PERIOD_NS=` the clock period. With the 4004 and 74181 sources the same scripts reproduce the numbers in those repos.
