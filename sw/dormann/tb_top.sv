// Top for the Dormann functional test under Verilator (Homer): m6502_system with its clock and reset driven from sim_main.cpp.
module tb_top (
  input  wire        clk,
  input  wire        res_n,
  output wire [15:0] a,
  output wire        sync,
  output wire        bus_conflict
);
  wire [7:0] d_out, bus, con_data; wire d_oe, rw, con_strobe;
  m6502_system #(.INIT_FILE(`MEMFILE)) dut (.clk(clk), .res_n(res_n), .rdy(1'b1), .irq_n(1'b1), .nmi_n(1'b1), .so_n(1'b1),
    .a(a), .d_out(d_out), .d_oe(d_oe), .rw(rw), .sync(sync), .bus(bus), .con_data(con_data), .con_strobe(con_strobe),
    .bus_conflict(bus_conflict));
endmodule
