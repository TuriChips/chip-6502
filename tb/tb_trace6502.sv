// Write-trace testbench on the m6502 pins (C5): the program (-DMEMFILE) writes results to $7000 and $7001; every such write must equal the next byte of +EXP (one hex byte per
// line, N lines = +N). Other writes go to RAM (below 8000; ROM above ignores writes). IRQ, NMI, RDY and SO inactive. No X/Z on the outputs once SYNC has been seen.
`timescale 1ns/1ps
module tb_trace6502;
  reg clk = 0, res_n = 0, rdy = 1, irq_n = 1, nmi_n = 1, so_n = 1;
  wire [15:0] a; wire [7:0] d_out; wire d_oe, rw, sync; wire [7:0] d_in;
  reg [7:0] mem [0:65535]; reg [7:0] exp [0:2000000];
  m6502 dut (.clk(clk), .res_n(res_n), .a(a), .d_in(d_in), .d_out(d_out), .d_oe(d_oe), .rw(rw), .sync(sync), .rdy(rdy), .irq_n(irq_n), .nmi_n(nmi_n), .so_n(so_n));
  assign d_in = mem[a];
  always #5 clk = ~clk;
  integer n = 0, got = 0, errors = 0, i, seen = 0; string expf;
  initial begin
    for (i = 0; i < 65536; i = i + 1) mem[i] = 8'h00;
    $readmemh(`MEMFILE, mem);
    if (!$value$plusargs("EXP=%s", expf)) begin $display("FAIL no +EXP"); $finish; end
    if (!$value$plusargs("N=%d", n) || n == 0) begin $display("FAIL empty or missing +N"); $finish; end
    $readmemh(expf, exp);
    repeat (12) @(posedge clk); @(negedge clk); res_n = 1;
  end
  always @(negedge clk) if (res_n) begin
    if (sync === 1'b1) seen = 1;
    if (seen && ^{a, d_out, d_oe, rw, sync} === 1'bx && !(rw === 1'b1 && ^{a, d_oe, rw, sync} !== 1'bx)) begin errors = errors + 1; if (errors < 10) $display("FAIL C7 X/Z on an output"); end
    if (rw === 1'b0) begin
      if (a == 16'h7000 || a == 16'h7001) begin
        if (d_out !== exp[got]) begin errors = errors + 1; if (errors < 10) $display("FAIL write %0d (case %0d, %s): expected %h got %h", got, got / 2, a == 16'h7000 ? "A" : "P", exp[got], d_out); end
        got = got + 1;
        if (got == n) begin $display("%s: %0d values, %0d errors", errors ? "FAIL" : "PASS", n, errors); $finish; end
      end else if (a < 16'h8000) mem[a] = d_out;
    end
  end
endmodule
