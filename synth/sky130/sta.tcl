# Leo: register-to-register timing of the mapped netlist (no placement, ideal wires, as in flow.tcl).
# Env: LIB (filtered tt liberty), NETLIST, TOP, PERIOD_NS. Typical corner: sky130_fd_sc_hd__tt_025C_1v80.
set S $::env(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd
read_lef $S/techlef/sky130_fd_sc_hd__nom.tlef
read_lef $S/lef/sky130_fd_sc_hd.lef
read_liberty $::env(LIB)
read_verilog $::env(NETLIST)
link_design $::env(TOP)
create_clock -name clk -period $::env(PERIOD_NS) [get_ports clk]
puts "== worst register-to-register path"
report_checks -from [all_registers -clock_pins] -to [all_registers -data_pins] -path_delay max -format full -digits 3
puts "== worst path to any endpoint"
report_checks -path_delay max -format end -group_count 3
exit
