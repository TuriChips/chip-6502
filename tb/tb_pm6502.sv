// MOS Programming Manual examples on m6502_system (spec 9 item 3). Runs the program in -DMEMFILE and compares the bytes written to $7000 with +EXP (one hex byte per line, +N bytes).
// Optional timing check: +FROM=<hex addr> +TO=<hex addr> +CLOCKS=<n>: the clocks between the first SYNC cycle fetching from FROM and the first SYNC cycle fetching from TO must be n
// (RDY stays 1, so one clock = one cycle). Also fails on X/Z on any output or bus_conflict after the first SYNC (as C7).
`timescale 1ns/1ps
module tb_pm6502;
  reg clk = 0, res_n = 0, rdy = 1, irq_n = 1, nmi_n = 1, so_n = 1;
  wire [15:0] a; wire [7:0] d_out, bus, con_data; wire d_oe, rw, sync, con_strobe, bus_conflict;
  m6502_system #(.INIT_FILE(`MEMFILE)) dut (.clk(clk), .res_n(res_n), .rdy(rdy), .irq_n(irq_n), .nmi_n(nmi_n), .so_n(so_n), .a(a), .d_out(d_out), .d_oe(d_oe), .rw(rw),
    .sync(sync), .bus(bus), .con_data(con_data), .con_strobe(con_strobe), .bus_conflict(bus_conflict));
  always #5 clk = ~clk;
  reg [7:0] exp [0:100000]; integer n = 0, got = 0, errors = 0, cyc = 0, limit = 0, seen = 0;
  integer from_a = -1, to_a = -1, want = -1, t0 = -1, t1 = -1; string expf;
  initial begin
    if (!$value$plusargs("CLOCKS_LIMIT=%d", limit)) limit = 2000000;
    if (!$value$plusargs("EXP=%s", expf)) begin $display("FAIL no +EXP"); $finish; end
    if (!$value$plusargs("N=%d", n) || n == 0) begin $display("FAIL empty or missing +N"); $finish; end
    void'($value$plusargs("FROM=%h", from_a)); void'($value$plusargs("TO=%h", to_a)); void'($value$plusargs("CLOCKS=%d", want));
    $readmemh(expf, exp);
    repeat (12) @(posedge clk); @(negedge clk); res_n = 1;
  end
  always @(negedge clk) if (res_n) begin
    cyc = cyc + 1; if (sync === 1'b1) seen = 1;
    if (seen) begin
      if (^{a, d_out, d_oe, rw, sync, bus, bus_conflict} === 1'bx) begin errors = errors + 1; if (errors < 10) $display("FAIL X/Z on an output at clock %0d", cyc); end
      if (bus_conflict !== 1'b0) begin errors = errors + 1; if (errors < 10) $display("FAIL bus_conflict at clock %0d", cyc); end
      if (sync === 1'b1 && a == from_a && t0 < 0) t0 = cyc;
      if (sync === 1'b1 && a == to_a && t0 >= 0 && t1 < 0) t1 = cyc;
      if (rw === 1'b0 && a == 16'h7000) begin
        if (got < n && d_out !== exp[got]) begin errors = errors + 1; if (errors < 10) $display("FAIL write %0d: expected %h got %h", got, exp[got], d_out); end
        got = got + 1;
      end
    end
    if (got >= n && (want < 0 || t1 >= 0)) begin
      if (got > n) begin errors = errors + 1; $display("FAIL more writes than expected"); end
      if (want >= 0 && t1 - t0 != want) begin errors = errors + 1; $display("FAIL timing: %0d clocks from %h to %h, manual says %0d", t1 - t0, from_a, to_a, want); end
      $display("%s: %0d bytes compared%s, %0d errors", errors ? "FAIL" : "PASS", n, want >= 0 ? $sformatf(", %0d clocks checked", t1 - t0) : "", errors); $finish;
    end
    if (cyc > limit) begin $display("FAIL timeout (%0d writes of %0d)", got, n); $finish; end
  end
endmodule
