// System-level testbench on m6502_system (C7, spec 7/8): runs a program from -DMEMFILE and checks, on every clock after the first SYNC: no X/Z on any output of the system
// (CPU pins, bus, con_data, con_strobe, bus_conflict) and bus_conflict = 0; and compares the writes to $7000/$7001 with +EXP (one hex byte per line, +N bytes).
// +EXPECT_CONFLICT=1: mutant mode: PASS only if bus_conflict was seen high (the positive case: a check that never saw a 1 isn't proven, spec 8); trace and X/Z checks off.
`timescale 1ns/1ps
module tb_sys6502;
  reg clk = 0, res_n = 0, rdy = 1, irq_n = 1, nmi_n = 1, so_n = 1;
  wire [15:0] a; wire [7:0] d_out, bus, con_data; wire d_oe, rw, sync, con_strobe, bus_conflict;
  m6502_system #(.INIT_FILE(`MEMFILE)) dut (.clk(clk), .res_n(res_n), .rdy(rdy), .irq_n(irq_n), .nmi_n(nmi_n), .so_n(so_n), .a(a), .d_out(d_out), .d_oe(d_oe), .rw(rw),
    .sync(sync), .bus(bus), .con_data(con_data), .con_strobe(con_strobe), .bus_conflict(bus_conflict));
  always #5 clk = ~clk;
  reg [7:0] exp [0:2000000]; integer n = 0, got = 0, errors = 0, cyc = 0, limit = 0, conflicts = 0, expect_conflict = 0, seen = 0; string expf;
  initial begin
    if (!$value$plusargs("CLOCKS=%d", limit)) limit = 5000000;
    if (!$value$plusargs("EXPECT_CONFLICT=%d", expect_conflict)) expect_conflict = 0;
    if (!expect_conflict) begin
      if (!$value$plusargs("EXP=%s", expf)) begin $display("FAIL no +EXP"); $finish; end
      if (!$value$plusargs("N=%d", n) || n == 0) begin $display("FAIL empty or missing +N"); $finish; end
      $readmemh(expf, exp);
    end
    repeat (12) @(posedge clk); @(negedge clk); res_n = 1;
  end
  always @(negedge clk) if (res_n) begin
    cyc = cyc + 1; if (sync === 1'b1) seen = 1;
    if (bus_conflict === 1'b1) conflicts = conflicts + 1;
    if (seen && !expect_conflict) begin
      if (^{a, d_out, d_oe, rw, sync, bus, con_data, con_strobe, bus_conflict} === 1'bx) begin errors = errors + 1; if (errors < 10) $display("FAIL C7 X/Z on an output at clock %0d", cyc); end
      if (bus_conflict !== 1'b0) begin errors = errors + 1; if (errors < 10) $display("FAIL C7 bus_conflict at clock %0d", cyc); end
      if (rw === 1'b0 && (a == 16'h7000 || a == 16'h7001)) begin
        if (d_out !== exp[got]) begin errors = errors + 1; if (errors < 10) $display("FAIL write %0d: expected %h got %h", got, exp[got], d_out); end
        got = got + 1;
      end
    end
    if (expect_conflict && conflicts > 0) begin $display("PASS: bus_conflict rose (%0d clocks) as expected for the mutant", conflicts); $finish; end
    if (!expect_conflict && got == n && n > 0) begin $display("%s: %0d writes compared, %0d errors, bus_conflict clocks %0d", errors ? "FAIL" : "PASS", n, errors, conflicts); $finish; end
    if (cyc > limit) begin $display("FAIL timeout%0s", expect_conflict ? ": bus_conflict never rose" : ""); $finish; end
  end
endmodule
