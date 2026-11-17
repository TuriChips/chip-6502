// Top for the 6502 demo under Verilator (Homer): m6502_system, clock and reset from sim_main.cpp, console port outputs.
module tb_top (
  input  wire        clk,
  input  wire        res_n,
  output wire [15:0] a,
  output wire        sync,
  output wire        bus_conflict,
  output wire [7:0]  con_data,
  output wire        con_strobe
);
  wire [7:0] d_out, bus; wire d_oe, rw;
  m6502_system #(.INIT_FILE(`MEMFILE)) dut (.clk(clk), .res_n(res_n), .rdy(1'b1), .irq_n(1'b1), .nmi_n(1'b1), .so_n(1'b1),
    .a(a), .d_out(d_out), .d_oe(d_oe), .rw(rw), .sync(sync), .bus(bus), .con_data(con_data), .con_strobe(con_strobe),
    .bus_conflict(bus_conflict));
endmodule
